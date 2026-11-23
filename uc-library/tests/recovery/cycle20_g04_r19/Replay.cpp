#include "presonus/mixer_state/MixerState.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>

namespace {
struct Deletions {
  std::array<void *, 3> records{};
  const void *backing = nullptr;
  std::array<const char *, 4> events{};
  unsigned count = 0;
};

Deletions *tracked = nullptr;
constexpr const char *slots[] = {"0", "1", "2"};

void release(void *storage, bool array, bool sized) noexcept {
  if (tracked) {
    auto &trace = *tracked;
    if (trace.count >= trace.events.size() || sized)
      std::abort();
    const char *event = nullptr;
    if (array) {
      if (storage && storage == trace.backing)
        event = "backing";
    } else if (!storage) {
      event = "null";
    } else {
      for (unsigned index = 0; index < trace.records.size(); ++index)
        if (storage == trace.records[index]) {
          event = slots[index];
          trace.records[index] = nullptr;
          break;
        }
    }
    if (!event)
      std::abort();
    trace.events[trace.count++] = event;
  }
  std::free(storage);
}
} // namespace

void operator delete(void *storage) noexcept { release(storage, false, false); }
void operator delete[](void *storage) noexcept {
  release(storage, true, false);
}
void operator delete(void *storage, std::size_t) noexcept {
  release(storage, false, true);
}
void operator delete[](void *storage, std::size_t) noexcept {
  release(storage, true, true);
}

int main() {
  using Presonus::IPresetHandler;
  using Presonus::MixerClientComponentBase;
  using PresetVector = Core::Vector<IPresetHandler::Preset *>;
  MixerClientComponentBase mixer;
  int capacity = 0;
  std::string layout;
  while (std::cin >> capacity >> layout) {
    if ((capacity != 0 && capacity != 8) || layout.size() > 3)
      return 1;
    PresetVector presets(capacity, 1);
    Deletions trace;
    trace.backing = presets.getItems();
    if (presets.getCapacity() != capacity ||
        (capacity != 0) != bool(trace.backing))
      return 2;
    if (layout != "-") {
      for (unsigned index = 0; index < layout.size(); ++index) {
        if (layout[index] != '0' && layout[index] != '1')
          return 1;
        auto *raw = layout[index] == '1' ? ::operator new(24) : nullptr;
        trace.records[index] = raw;
        if (!presets.add(static_cast<IPresetHandler::Preset *>(raw)))
          return 2;
      }
    }
    tracked = &trace;
    mixer.clearPresets(presets);
    tracked = nullptr;
    for (unsigned index = 0; index < trace.count; ++index)
      std::cout << trace.events[index] << ' ';
    for (const auto *record : trace.records)
      if (record)
        return 3;
    std::cout << presets.count() << ' ' << presets.getCapacity() << ' '
              << bool(presets.getItems()) << '\n';

    Deletions repeat;
    tracked = &repeat;
    mixer.clearPresets(presets);
    tracked = nullptr;
    if (repeat.count)
      return 4;
  }
  return std::cin.eof() ? 0 : 1;
}
