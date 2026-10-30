#pragma once
namespace presonus::dsp {
// Independent explicit startup API. Existing EQ and Compressor bootstraps must
// complete first. Labels are explicit caller choices, not recovered defaults;
// nonnull ASCII strings of at most31 bytes are copied into actual CCL buffers.
// Setup is serialized before any Gate singleton/concurrent registry use.
void registerGateSourcePortProviders(const char *onLabel, const char *offLabel);
bool gateSourcePortProvidersReady() noexcept;
} // namespace presonus::dsp
