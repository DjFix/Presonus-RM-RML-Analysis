#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string_view>

namespace {
template <class T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}
} // namespace

int main() {
  Presonus::Mixer::MixerComponentBase base;
  std::uint32_t cascade = 0x12345678;
  Presonus::Mixer::RackMixerComponent mixer(base, cascade);
  Presonus::Panel::ControlRegistrar registrar;

  for (unsigned tag = 0; tag < 256; ++tag) {
    for (bool null : {false, true}) {
      std::array<unsigned char, 3> payload{
          0x31, static_cast<unsigned char>(tag), 0x79};
      const auto mixerBefore = snapshot(mixer);
      const auto baseBefore = snapshot(base);
      const auto registrarBefore = snapshot(registrar);
      mixer.controlChanged(registrar, static_cast<unsigned char>(tag),
                           null ? nullptr : &payload[1]);
      const bool changed =
          snapshot(mixer) != mixerBefore || snapshot(base) != baseBefore ||
          snapshot(registrar) != registrarBefore || cascade != 0x12345678;
      std::cout << tag << ' ' << null << ' ' << changed;
      for (unsigned char value : payload)
        std::cout << ' ' << static_cast<unsigned>(value);
      std::cout << '\n';
    }
  }
}
