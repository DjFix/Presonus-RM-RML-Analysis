#include "core/portable/coreparams.h"
#include "presonus/mixer/FxTypeFormatter.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"

#include <array>
#include <cassert>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string_view>

namespace {
const Core::Formatter *receiver;
int registrations;
} // namespace

extern "C" void realAdd(Core::Formatter *) asm(
    "__real__ZN4Core17FormatterRegistry3addEPNS_9FormatterE");
extern "C" void wrapAdd(Core::Formatter *formatter) asm(
    "__wrap__ZN4Core17FormatterRegistry3addEPNS_9FormatterE");

extern "C" void wrapAdd(Core::Formatter *formatter) {
  if (std::string_view(formatter->getName()) == "fxtype") {
    if (receiver)
      assert(receiver == formatter);
    receiver = formatter;
    ++registrations;
  }
  realAdd(formatter);
}

int main(int argc, char **argv) {
  using Core::Formatter;
  using Core::FormatterRegistry;
  using Core::Portable::NumericParam;
  using Core::Portable::ParamInfo;
  using Presonus::Mixer::FxTypeFormatter;
  using Presonus::Mixer::XmenFormatterInitializer;

  assert(argc == 3);
  assert(FormatterRegistry::find("fxtype") == nullptr);
  const Formatter *first = nullptr;
  for (int call = 0; call < 3; ++call) {
    XmenFormatterInitializer::addClass<FxTypeFormatter>();
    const auto *current = FormatterRegistry::find("fxtype");
    assert(current && current == receiver);
    if (first)
      assert(current == first);
    first = current;
  }
  assert(registrations == 3);

  ParamInfo info{};
  info.type = ParamInfo::kInt;
  info.tag = 3;
  std::strcpy(info.name, "slot_type");
  info.maxValue = 8.f;
  info.defaultValue = std::stof(argv[1]);
  info.deltaValue = 1.f;
  info.unitName = "fxtype";
  info.curveName = "";
  info.title = "FX Slot Type";
  NumericParam param(info, false);
  assert(param.getTag() == 3 && param.getFormatter() == first);

  std::array<char, 64> output;
  output.fill(static_cast<char>(0xd9));
  const int capacity = std::stoi(argv[2]);
  assert(capacity >= 0 && capacity <= static_cast<int>(output.size()));
  param.toString(output.data(), capacity);
  for (auto i = capacity; i < static_cast<int>(output.size()); ++i)
    assert(static_cast<unsigned char>(output[i]) == 0xd9);

  auto printed = output;
  Formatter::Data data{&param, output.data(), capacity, param.getValue(),
                       nullptr};
  const bool scanned = first->scan(data);
  assert(!scanned && data.value == param.getValue() && output == printed);
  std::cout << registrations << ' ' << first->getName() << ' ' << scanned
            << '\n';
  for (auto i = 0; i < capacity; ++i)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << static_cast<unsigned>(static_cast<unsigned char>(output[i]));
  std::cout << '\n';
}
