#pragma once
namespace presonus::dsp {
// Independent explicit bootstrap. Existing EQ source bootstrap must complete
// first, before first Compressor singleton/concurrent registry use. No
// autostart.
void registerCompressorSourcePortProviders();
bool compressorSourcePortProvidersReady() noexcept;
} // namespace presonus::dsp
