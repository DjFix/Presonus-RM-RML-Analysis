#include "presonus/panel/WolverinePanelComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
using namespace Presonus::Panel;
namespace {
void *watched = nullptr;
int frees = 0, sizedFrees = 0, childrenDestroyed = 0, paramsDestroyed = 0;
void *parameters[64]{};
int parameterCount = 0;
struct Child : Core::Portable::Component {
  Child() : Component("owned-child") {}
  ~Child() override { ++childrenDestroyed; }
};
struct Task : PanelTask {
  int calls = 0;
  bool idle() override {
    ++calls;
    return false;
  }
};
struct Dependencies : presonus::rackpanel_port::Dependencies {
  Core::Portable::Component parameters{"borrowed"};
  presonus::panel_binding::ControlGroupState groupState;
  ControlGroup controls{groupState};
  std::vector<presonus::rackpanel_port::Channel> list;
  ControlGroup &group(int) override { return controls; }
  Core::Portable::Component &monitorParameters() override { return parameters; }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    return list;
  }
  int numClients() const override { return 1; }
  void removeDelegate(RackPanelComponent &) override { std::abort(); }
};
void populate(RackPanelComponent &object, int count, Task &borrowed,
              Control &control) {
  static const Core::Portable::ParamInfo info = {
      1,   7, "lifecycle", 0.f,     100.f,   4.f, 0.f,
      1.f, 0, nullptr,     nullptr, nullptr, "",  nullptr};
  for (int i = 0; i < count; ++i) {
    object.addParameters(&info, 1);
    parameters[i] = object.getParameterAt(i);
    object.addChild(new Child);
    if (!object.tasks.add(&borrowed))
      std::abort();
    // Deliberately borrowed pointer entries; vector destruction must never
    // dereference or delete them. The valid task pointer is also used above.
    object.meterLEDs.push_back(&control);
    object.clipLEDs.push_back(&control);
    object.phantomLEDs.push_back(&control);
  }
  control.setParameter(object.getParameterAt(0), 0);
  object.idleTasks();
}
} // namespace
void operator delete(void *p) noexcept {
  if (p == watched)
    ++frees;
  for (int i = 0; i < parameterCount; ++i)
    if (p == parameters[i])
      ++paramsDestroyed;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept {
  if (p == watched)
    ++sizedFrees;
  for (int i = 0; i < parameterCount; ++i)
    if (p == parameters[i])
      ++paramsDestroyed;
  std::free(p);
}
int main(int argc, char **argv) {
  bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  int variant, count, baseCalls, deleteCalls;
  while (std::cin >> variant >> count >> baseCalls >> deleteCalls) {
    if (count < 1 || count > 64 || baseCalls != 1 || deleteCalls != variant)
      return 2;
    Dependencies dependencies;
    Task borrowed;
    Control control{21};
    childrenDestroyed = paramsDestroyed = frees = sizedFrees = 0;
    parameterCount = 0;
    void *storage = ::operator new(sizeof(WolverinePanelComponent));
    watched = storage;
    if (provider) {
      // Original observed base boundary executes the actual base destructor;
      // the native deleting boundary invokes genuine global unsized delete.
      auto *object = new (storage) RackPanelComponent(dependencies);
      populate(*object, count, borrowed, control);
      parameterCount = count;
      object->RackPanelComponent::~RackPanelComponent();
      if (deleteCalls)
        ::operator delete(storage);
    } else {
      auto *object = new (storage) WolverinePanelComponent(
          WolverineSourcePortConstruction{}, dependencies);
      populate(*object, count, borrowed, control);
      parameterCount = count;
      if (variant)
        delete object;
      else
        object->~WolverinePanelComponent();
    }
    std::cout << childrenDestroyed << ' ' << paramsDestroyed << ' '
              << borrowed.calls << ' ' << frees << ' ' << sizedFrees << ' '
              << dependencies.parameters.getName() << ' '
              << (control.getParameter() == nullptr) << '\n';
    watched = nullptr;
    parameterCount = 0;
    if (!variant)
      ::operator delete(storage);
  }
}
