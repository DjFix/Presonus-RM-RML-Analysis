#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>
#include <map>
#include <string>

using namespace Core::Portable;
using namespace Presonus::Surface;

namespace {
struct Observer : ParamObserverBase {
  void paramChanged(Parameter *, int) override {}
};
struct Probe : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
struct Tree : Component {
  using Component::Component;
  void attach(Probe *probe) { paramList.add(probe); }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int inputTag = std::stoi(argv[1]);
  std::map<int, ParamInfo> infos;
  std::map<int, Probe *> params;
  Observer observer;
  Tree tree("root");
  auto *screen = new Tree("mainscreen");
  tree.addChild(screen);
  auto insert = [&](int tag, Tree &component) {
    const ParamInfo description = PARAM_TOGGLE(tag, "parameter", 0, 0, 0);
    auto *probe = new Probe(infos.emplace(tag, description).first->second);
    component.attach(probe);
    params.emplace(tag, probe);
  };
  for (const int tag : {100, 101, 102, 103, 104, 105, 108, 109, 110, 115, 116,
                        117, 118, 903, 1000})
    insert(tag, tree);
  for (const int tag : {2, 31, 32, 33, 34, 38})
    insert(tag, *screen);
  for (const int tag : {100, 105, 115})
    params.at(tag)->setValue(1.f);
  for (const int tag : {31, 32, 33, 34, 38, 903, 1000})
    params.at(tag)->addObserver(&observer);
  presonus::surface::RootServices services;
  services.rootParameters = &tree;
  services.children = &tree;
  services.observer = &observer;
  services.touchscreenActive = true;
  services.mainScreens.push_back(
      {screen, reinterpret_cast<MainScreenComponent *>(std::uintptr_t{0x1234}),
       "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
       "_ZTIN8Presonus7Surface19MainScreenComponentE", 0x1a0434});
  SurfaceRootComponent target;
  target.bindServices(services);
  const ParamInfo inputInfo = PARAM_TOGGLE(inputTag, "input", 0, 0, 0);
  NumericParam input(inputInfo);
  target.onMainScreenParamChanged(&input);
  std::cout << "state " << services.touchscreenActive;
  for (const int tag : {100, 105, 115})
    std::cout << ' ' << static_cast<int>(params.at(tag)->getValue());
  for (const int tag : {31, 32, 33, 34, 38, 903, 1000}) {
    std::cout << ' ' << params.at(tag)->observers();
    params.at(tag)->removeObserver(&observer);
  }
  std::cout << '\n';
}
