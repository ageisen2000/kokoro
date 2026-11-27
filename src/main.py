#!/usr/bin/env python3
"""Kokoro-82M text-to-speech server speaking the Wyoming protocol.

A self-owned implementation for this homelab:
- serves Wyoming ``Describe`` / ``Synthesize`` events over TCP or a Unix socket
- voices are read directly from the baked Kokoro model
- default voice is ``af_heart``
"""
import argparse
import asyncio
import logging
import signal
import re
from functools import partial

import numpy as np

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import (
    Attribution,
    Describe,
    Info,
    TtsProgram,
    TtsVoice,
    TtsVoiceSpeaker,
)
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize

from kokoro_onnx import Kokoro
from kokoro_onnx.config import SAMPLE_RATE

_LOGGER = logging.getLogger("kokoro")

DEFAULT_VOICE = "af_heart"


def split_sentences(text: str) -> list[str]:
    """Split text into sentences at punctuation followed by whitespace."""
    text = " ".join(text.strip().split())
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def language_for(voice_id: str) -> str:
    """Infer a language code from a voice id's prefix."""
    prefix = voice_id.split("_", 1)[0].lower()
    if prefix.startswith("a"):
        return "en"
    if prefix.startswith("b"):
        return "en"
    if prefix.startswith("i"):
        return "it"
    if prefix.startswith("j"):
        return "jp"
    if prefix.startswith("z"):
        return "cn"
    if prefix.startswith("e"):
        return "es"
    if prefix.startswith("f"):
        return "fr"
    if prefix.startswith("h"):
        return "hi"
    return "en"


def lang_code_for(voice_id: str) -> str:
    """Lang tag passed to the model (en-us vs en-gb)."""
    return "en-us" if voice_id.startswith("a") else "en-gb"


def build_voices(model: Kokoro) -> list[TtsVoice]:
    """Build Wyoming voice descriptor from the model's installed voices."""
    voices = []
    for voice_id in sorted(model.voices.keys()):
        speaker_name = voice_id.split("_", 1)[1] if "_" in voice_id else voice_id
        voices.append(
            TtsVoice(
                name=voice_id,
                description=voice_id,
                attribution=Attribution(name="", url=""),
                installed=True,
                version=None,
                languages=[language_for(voice_id)],
                speakers=[TtsVoiceSpeaker(name=speaker_name)],
            )
        )
    return voices


class KokoroEventHandler(AsyncEventHandler):
    def __init__(self, wyoming_info, kokoro_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kokoro = kokoro_model
        self.wyoming_info_event = wyoming_info.event()

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            return True

        if Synthesize.is_type(event.type):
            await self._handle_synthesize(event)
            return True

        _LOGGER.debug("Ignoring event: %s", event.type)
        return True

    async def _handle_synthesize(self, event: Event) -> None:
        try:
            synthesize = Synthesize.from_event(event)
            voice_name = (
                synthesize.voice.name if synthesize.voice and synthesize.voice.name else DEFAULT_VOICE
            )
            sentences = split_sentences(synthesize.text)

            audio_sent = False
            for sentence in sentences:
                stream = self.kokoro.create_stream(
                    sentence,
                    voice=voice_name,
                    speed=1.0,
                    lang=lang_code_for(voice_name),
                )
                async for audio, sample_rate in stream:
                    if not audio_sent:
                        await self.write_event(
                            AudioStart(rate=SAMPLE_RATE, width=2, channels=1).event()
                        )
                        audio_sent = True
                    audio_int16 = (audio * 32767).astype(np.int16)
                    await self.write_event(
                        AudioChunk(
                            rate=SAMPLE_RATE,
                            width=2,
                            channels=1,
                            audio=audio_int16.tobytes(),
                        ).event()
                    )

            if audio_sent:
                await self.write_event(AudioStop().event())
        except Exception as err:
            _LOGGER.exception("Synthesis failed: %s", err)
            await self.write_event(
                Error(text=str(err), code=err.__class__.__name__).event()
            )


async def main():
    parser = argparse.ArgumentParser(description="Kokoro Wyoming-protocol TTS server")
    parser.add_argument("--uri", default="tcp://0.0.0.0:10210", help="unix:// or tcp://")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        _LOGGER.setLevel(logging.DEBUG)

    model_path = "/app/kokoro-v1.0.onnx"
    voices_path = "/app/voices-v1.0.bin"
    kokoro_instance = Kokoro(model_path, voices_path)

    wyoming_voices = build_voices(kokoro_instance)

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="Kokoro",
                description="A fast, local, kokoro-based tts engine",
                attribution=Attribution(
                    name="Kokoro TTS",
                    url="https://huggingface.co/hexgrad/Kokoro-82M",
                ),
                installed=True,
                voices=wyoming_voices,
                version="1.0.0",
            )
        ]
    )

    _LOGGER.info("kokoro Wyoming TTS starting on %s", args.uri)
    server = AsyncServer.from_uri(args.uri)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(server.stop()))

    await server.run(partial(KokoroEventHandler, wyoming_info, kokoro_instance))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
