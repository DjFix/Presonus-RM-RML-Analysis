#include "presonus/mixer/ParamLink.hpp"
#include <cstring>
#include <iostream>
struct Watched : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
extern "C" void ctor1(
    void *, Core::Portable::Parameter *, const char *,
    bool) asm("_ZN8Presonus5Mixer9ParamLinkC1EPN4Core8Portable9ParameterEPKcb");
extern "C" void ctor2(
    void *, Core::Portable::Parameter *, const char *,
    bool) asm("_ZN8Presonus5Mixer9ParamLinkC2EPN4Core8Portable9ParameterEPKcb");
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.minValue = -100;
  info.maxValue = 100;
  int present, flag, longName;
  while (std::cin >> present >> flag >> longName) {
    Watched parameter(info);
    const char *name =
        longName ? "abcdefghijklmnopqrstuvwxyz0123456789LONG" : "";
    alignas(Presonus::Mixer::ParamLink) unsigned char
        bytes[sizeof(Presonus::Mixer::ParamLink)];
    (argv[1][0] == '1' ? ctor1 : ctor2)(bytes, present ? &parameter : nullptr,
                                        name, flag);
    auto *link = reinterpret_cast<Presonus::Mixer::ParamLink *>(bytes);
    const int added = parameter.observers();
    std::cout << (link->parameter() == (present ? &parameter : nullptr)) << ' '
              << link->portableFlag() << ' '
              << (link->portableTarget() == nullptr) << ' ' << added << ' '
              << std::strlen(link->name());
    parameter.setValue(
        4.5f, false); // Real callback with unbound target safely returns.
    link->~ParamLink();
    std::cout << ' ' << parameter.observers() << '\n';
  }
}
