#include "presonus/panel/temperature_control.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
namespace {
int integer(unsigned u) {
  int v;
  std::memcpy(&v, &u, 4);
  return v;
}
struct Param final : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  std::vector<std::pair<unsigned, unsigned>> calls;
  void setNormalized(float value, bool edit) override {
    unsigned bits;
    std::memcpy(&bits, &value, 4);
    calls.emplace_back(bits, edit);
    NumericParam::setNormalized(value, edit);
  }
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  if (!in)
    return 2;
  std::string op;
  unsigned value, present, count, wantedPointer, checked = 0;
  while (in >> op >> value >> present >> count) {
    std::vector<std::pair<unsigned, unsigned>> expected(count);
    for (auto &[v, e] : expected)
      in >> v >> e;
    in >> wantedPointer;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.tag = 1;
    info.minValue = 0;
    info.maxValue = 1;
    info.defaultValue = .5f;
    Param p(info);
    Presonus::Panel::TemperatureControl c(
        presonus::panel::TemperatureSourcePort{}, 7);
    presonus::panel::ControlAccess::parameter(c) = present ? &p : nullptr;
    if (op == "R")
      c.receiveValue(integer(value));
    else if (op == "K") {
      void *result = c.castTo(integer(value));
      assert((result == &c) == bool(wantedPointer));
      assert(result == nullptr || result == &c);
    } else
      return 3;
    if (p.calls != expected) {
      std::cerr << "case " << checked << " mismatch\n";
      return 4;
    }
    ++checked;
  }
  if (checked != 2418)
    return 5;
  std::cout << "{\"passed\":true,\"cases\":" << checked << ",\"no_IO\":true}\n";
}
