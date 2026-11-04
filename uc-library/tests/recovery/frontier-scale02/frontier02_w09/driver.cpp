#include "presonus/StormMuteGroupComponent.hpp"
#include <iostream>
#include <memory>
#include <vector>
using namespace Core::Portable;
struct Services : presonus::storm_mute_port::Services {
  void refreshSip() override { throw 1; }
  void activate(unsigned int) override { throw 1; }
  Component *connectedClient() override { throw 1; }
  void muteGroupStored(int) override { throw 1; }
  bool load(presonus::storm_mute_port::Group &) override { throw 1; }
};
struct Param : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
static std::vector<Parameter *> params;
static IParamObserver *expected;
static std::vector<int> calls;
extern "C" void realRemove(Parameter *, IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *p, IParamObserver *o) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrapRemove(Parameter *p, IParamObserver *o) {
  if (o != expected)
    throw 2;
  int id = 0;
  while (params.at(id) != p)
    ++id;
  calls.push_back(id);
  realRemove(p, o);
}
int main(int argc, char **argv) {
  int n = std::stoi(argv[1]);
  int mode = std::stoi(argv[2]);
  Services services;
  presonus::storm_mute_port::State state(services);
  Presonus::StormMuteGroupComponent component(state);
  expected = &component;
  ParamInfo info = {};
  std::vector<std::unique_ptr<Param>> objects;
  for (int i = 0; i < 4; ++i) {
    objects.emplace_back(new Param(info));
    params.push_back(objects.back().get());
    objects.back()->addObserver(expected);
  }
  for (int i = 0; i < n; ++i)
    state.cleanupParameters.add(params[mode ? i % 2 : i % 4]);
  component.cleanup();
  for (int id : calls)
    std::cout << id << ' ';
  std::cout << '\n';
  for (auto &p : objects)
    std::cout << p->observers() << ' ';
  std::cout << '\n';
}
