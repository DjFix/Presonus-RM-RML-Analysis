#include "presonus/surface/DawFxPageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
struct State {
  bool folder;
  int count;
  std::vector<std::string> trace;
};
struct Mode : NumericParam {
  State &s;
  Mode(const ParamInfo &i, State &state) : NumericParam(i), s(state) {}
  ParamValue getValue() const override {
    s.trace.push_back("value");
    return NumericParam::getValue();
  }
};
namespace Presonus::Surface {
struct DawFxTestAccess {
  static int a(const DawFxPageComponent &p) { return p.insertOffset_; }
  static int z(const DawFxPageComponent &p) { return p.sendOffset_; }
  static int slot(const DawFxPageComponent &p, const int &r) {
    return &r == &p.sendOffset_ ? 200 : 196;
  }
};
} // namespace Presonus::Surface
int main(int argc, char **argv) {
  if (argc != 9)
    return 2;
  int op = std::atoi(argv[1]), present = std::atoi(argv[2]);
  float value = std::strtof(argv[3], nullptr);
  State s{std::atoi(argv[4]) != 0, std::atoi(argv[5]), {}};
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.minValue = -100;
  info.maxValue = 100;
  Mode mode(info, s);
  mode.setValue(value);
  AliasParam alias(info);
  alias.setOriginal(&mode);
  s.trace.clear();
  presonus::surface::DawFxBindings b{&s,
                                     [](void *v) {
                                       auto &s = *static_cast<State *>(v);
                                       s.trace.push_back("folder");
                                       return s.folder;
                                     },
                                     [](void *v) {
                                       auto &s = *static_cast<State *>(v);
                                       s.trace.push_back("count");
                                       return s.count;
                                     },
                                     [](void *v, bool force) {
                                       auto &s = *static_cast<State *>(v);
                                       s.trace.push_back(force ? "update1"
                                                               : "update0");
                                     }};
  Presonus::Surface::DawFxPageComponent page(
      present ? &alias : nullptr, b, std::atoi(argv[6]), std::atoi(argv[7]));
  int result = 0;
  if (op == 1)
    page.setListOffset(std::atoi(argv[8]));
  if (op == 2)
    page.addListOffset(std::atoi(argv[8]));
  if (op == 3)
    result = page.getMaxListOffset();
  if (op == 4)
    result =
        Presonus::Surface::DawFxTestAccess::slot(page, page.getListOffset());
  if (op == 5)
    result = page.isSendMode();
  auto trace = s.trace;
  int a = Presonus::Surface::DawFxTestAccess::a(page),
      z = Presonus::Surface::DawFxTestAccess::z(page);
  std::cout << result << ' ' << a << ' ' << z;
  for (const auto &t : trace)
    std::cout << ' ' << t;
  std::cout << '\n';
}
