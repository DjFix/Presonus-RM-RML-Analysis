#pragma once
namespace presonus::dsp {
// Independent explicit source-port bootstrap, not an original application API.
void registerGEQSourcePortProviders();
bool geqSourcePortProvidersReady() noexcept;
} // namespace presonus::dsp
