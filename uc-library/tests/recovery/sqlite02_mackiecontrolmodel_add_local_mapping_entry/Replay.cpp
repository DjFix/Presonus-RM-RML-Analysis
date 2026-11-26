#include "presonus/MackieControlComponent.hpp"

#include <algorithm>
#include <bit>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

namespace {
using namespace Core::Portable;

std::string hex(std::string_view bytes) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  for (unsigned char ch : bytes) {
    result += digits[ch >> 4];
    result += digits[ch & 15];
  }
  return result;
}

std::uint32_t bits(float value) { return std::bit_cast<std::uint32_t>(value); }

struct Panel : Presonus::MackieControlComponent {
  explicit Panel(const std::string &kind) {
    model.setPanel(this);
    if (kind == "meter") {
      for (int base : {0, 0x4000})
        for (int i = 0; i < 8; ++i)
          numeric(base + i, 1.f);
    } else if (kind == "ring") {
      for (int base : {0x4400, 0x4500, 0x4600})
        for (int i = 0; i < 8; ++i)
          numeric(base + i, base == 0x4400 ? 3.f : 1.f);
    } else if (kind == "reset") {
      for (int i = 0; i < 8; ++i)
        numeric(0x2000 + i, 1.f, .5f);
      masterFader = numeric(0x9000, 1.f, .5f);
    } else if (kind == "display") {
      for (int base : {0x4700, 0x4800})
        for (int i = 0; i < 8; ++i) {
          auto *info = new ParamInfo{};
          info->type = ParamInfo::kString;
          info->tag = base + i;
          auto *parameter = new StringParam(*info, true);
          parameter->fromString("seed", false);
          paramList.add(parameter);
        }
    }
  }

  NumericParam *numeric(int tag, float max, float initial = 0.f) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->tag = tag;
    info->minValue = 0.f;
    info->maxValue = max;
    info->defaultValue = initial;
    auto *parameter = new NumericParam(*info, true);
    paramList.add(parameter);
    return parameter;
  }

  void updateLedState(int tag, int state) override {
    std::cout << "L " << tag << ' ' << state << '\n';
    MackieControlComponent::updateLedState(tag, state);
    assert(paramList.byTag(tag)->getValue() == static_cast<float>(state));
  }
  void updateMeter(int tag, float value) override {
    std::cout << "M " << tag << ' ' << bits(value) << '\n';
    MackieControlComponent::updateMeter(tag, value);
    assert(paramList.byTag(tag)->getValue() == std::clamp(value, 0.f, 1.f));
  }
  void updateValueBar(int tag, int mode, float value, bool enabled) override {
    std::cout << "V " << tag << ' ' << mode << ' ' << bits(value) << ' '
              << enabled << '\n';
    MackieControlComponent::updateValueBar(tag, mode, value, enabled);
    assert(paramList.byTag(tag + 0x100)->getValue() ==
           static_cast<float>(mode));
    assert(paramList.byTag(tag + 0x200)->getValue() ==
           std::clamp(value, 0.f, 1.f));
    assert(paramList.byTag(tag + 0x300)->getValue() ==
           static_cast<float>(enabled));
  }
  void updateFader(int tag, float value) override {
    std::cout << "F " << tag << ' ' << bits(value) << '\n';
    MackieControlComponent::updateFader(tag, value);
    assert(paramList.byTag(tag)->getValue() == value);
  }
  void updateTextDisplay(int tag, const char *text, int flags) override {
    std::cout << "T " << tag << ' ' << flags << ' ' << hex(text) << '\n';
    MackieControlComponent::updateTextDisplay(tag, text, flags);
    char actual[32];
    paramList.byTag(tag)->toString(actual, sizeof(actual));
    assert(std::string_view(actual) == text);
  }
};
} // namespace

int main() {
  std::string kind;
  if (!(std::cin >> kind))
    return 2;
  Panel panel(kind);
  auto &model = panel.model;
  if (kind == "mapping") {
    int count;
    Presonus::MackieControlModel::MappingEntry entry{};
    std::cin >> count >> entry.tag >> entry.note >> entry.stateIndex;
    for (int i = 0; i < count; ++i) {
      const Presonus::MackieControlModel::Entry row{2 * i, 2 * i + 1, i};
      model.entries.push_back(row);
      model.midiEntries.push_back(row);
      model.buttonStates.push_back(1);
    }
    model.addMapping(entry);
    for (const auto *rows : {&model.entries, &model.midiEntries}) {
      std::cout << "A " << rows->size() << '\n';
      for (auto row : *rows)
        std::cout << row.tag << ' ' << row.note << ' ' << row.stateIndex
                  << '\n';
    }
    const auto states = model.buttonStates.empty()
                            ? std::string_view{}
                            : std::string_view{reinterpret_cast<const char *>(
                                                   model.buttonStates.data()),
                                               model.buttonStates.size()};
    std::cout << "B " << hex(states) << '\n';
  } else if (kind == "meter" || kind == "ring") {
    int channel, value;
    while (std::cin >> channel >> value) {
      if (kind == "meter")
        model.onMessageMeter(channel, value);
      else
        model.onMessageVPotRing(channel, value);
    }
    if (kind == "meter") {
      std::cout << 'P';
      for (auto peak : model.meterPeaks)
        std::cout << ' ' << bits(peak);
      std::cout << '\n';
    }
  } else if (kind == "reset") {
    int mask;
    std::cin >> model.omitMaster >> mask;
    for (int i = 0; i < 9; ++i) {
      model.touched[i] = (mask >> i) & 1;
      model.faderValues[i] = i;
    }
    model.resetFaders();
    std::cout << "C "
              << hex({reinterpret_cast<const char *>(model.touched.data()), 9});
    for (auto cache : model.faderValues)
      std::cout << ' ' << cache;
    std::cout << '\n';
  } else if (kind == "display") {
    std::string data;
    std::cin >> data;
    assert(data.size() == model.displayData.size() * 2);
    for (std::size_t i = 0; i < model.displayData.size(); ++i)
      model.displayData[i] =
          static_cast<char>(std::stoi(data.substr(2 * i, 2), nullptr, 16));
    model.updateDisplayData();
  } else {
    return 2;
  }
}
