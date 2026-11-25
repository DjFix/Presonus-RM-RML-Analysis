#include "presonus/dsp/SLReverbController.hpp"
#include <bit>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  const int index = std::stoi(argv[1]);
  const auto valueBits = static_cast<std::uint32_t>(std::stoul(argv[2]));
  const std::string initial(argv[3]);
  presonus::dsp::ReverbPortState borrowed;
  Presonus::Dsp::SLReverbController borrowedController(borrowed);
  Presonus::Dsp::SLReverbController ownedController(3);
  auto &reverb =
      std::string(argv[4]) == "owned" ? ownedController : borrowedController;
  auto &state = reverb.reverbSourceState();
  if (initial.size() != 2 * state.memory.size())
    return 3;
  for (std::size_t i = 0; i < state.memory.size(); ++i)
    state.memory[i] = static_cast<std::byte>(
        std::stoul(initial.substr(2 * i, 2), nullptr, 16));
  const std::string presetHex(argv[5]);
  std::vector<std::byte> presets(presetHex.size() / 2);
  for (std::size_t i = 0; i < presets.size(); ++i)
    presets[i] = static_cast<std::byte>(
        std::stoul(presetHex.substr(2 * i, 2), nullptr, 16));
  state.presets = presets;
  state.dependency = [](std::uint32_t address,
                        std::array<std::uint32_t, 4> args) {
    std::cout << address;
    for (const auto argument : args)
      std::cout << ' ' << argument;
    std::cout << '\n';
  };
  Presonus::Dsp::Controller &control = reverb;
  auto volatile setter = &Presonus::Dsp::Controller::setValue;
  const auto result = (control.*setter)(index, std::bit_cast<float>(valueBits));
  std::cout << std::bit_cast<std::uint32_t>(result) << '\n';
  for (const auto octet : state.memory)
    std::cout << std::hex << std::setfill('0') << std::setw(2)
              << std::to_integer<unsigned>(octet);
  std::cout << '\n';
}
