#include "presonus/MixerClientComponentBase.hpp"
#include <iostream>

int main() {
  using Presonus::IPresetHandler;
  using Roster = Presonus::PortableMixerState::PresetRoster;
  Presonus::MixerClientComponentBase mixer;
  IPresetHandler::Preset first, third, fallback;
  IPresetHandler::Preset *const entries[] = {&first, nullptr, &third};
  IPresetHandler::Preset *const identities[] = {nullptr, &first, &third,
                                                &fallback};
  const char *const names[] = {nullptr, "ignored local label", ""};
  auto *const oldError = Roster::getError();
  Roster::getError() = &fallback;
  int type = 0, index = 0, count = 0;
  unsigned label = 0;
  while (std::cin >> type >> index >> count >> label) {
    if (count < 0 || count > 3 || label >= std::size(names))
      return 1;
    const Roster roster(entries, count);
    auto &rosters = mixer.portableState().presetRosters;
    const auto slot = static_cast<unsigned>(type);
    if (slot < rosters.size())
      rosters[slot] = count == 0 && label == 0 ? nullptr : &roster;
    const auto presetType = static_cast<IPresetHandler::PresetType>(type);
    const auto *result = mixer.getPreset(presetType, index, names[label]);
    unsigned found = 0;
    while (found < std::size(identities) && result != identities[found])
      ++found;
    std::cout << found << '\n';
    if (slot < rosters.size())
      rosters[slot] = nullptr;
  }
  Roster::getError() = oldError;
  return std::cin.eof() ? 0 : 1;
}
