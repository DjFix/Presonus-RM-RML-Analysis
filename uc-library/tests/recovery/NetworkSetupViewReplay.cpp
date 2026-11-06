#include "core/portable/gui/corelistview.h"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/surface/RadioToggleButton.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
struct Event {
  int code;
  uint32_t value;
  int edit;
};
std::vector<Event> events;
uint32_t bits(float f) {
  uint32_t v;
  std::memcpy(&v, &f, 4);
  return v;
}
float number(uint32_t v) {
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}
void *watched = nullptr;
int frees = 0, detaches = 0;
bool failNextAllocation = false;
struct BitmapProbe : Core::Portable::Bitmap {
  int count() const { return useCount; }
};
BitmapProbe *first = nullptr, *second = nullptr;
struct Param : NumericParam {
  float raw = 0;
  bool capture = false;
  Param()
      : NumericParam(PARAM_FLOAT(9, "choice", -1.e30f, 1.e30f, 0, 0, nullptr,
                                 nullptr, 0, 0)) {}
  void beginEdit() override {
    if (capture)
      events.push_back({1, 0, 0});
    NumericParam::beginEdit();
  }
  float getValue() const override {
    if (capture)
      events.push_back({2, 0, 0});
    return raw;
  }
  void setValue(float v, bool edit) override {
    if (capture)
      events.push_back({3, bits(v), int(edit)});
    raw = v;
    NumericParam::setValue(v, edit);
  }
  void endEdit() override {
    if (capture)
      events.push_back({4, 0, 0});
    NumericParam::endEdit();
  }
};
struct Probe : Presonus::Surface::RadioToggleButton {
  using RadioToggleButton::RadioToggleButton;
  void setDown(bool v) { down = v; }
  bool getDown() const { return down; }
};
struct Parameters : Component {
  void add(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct Dependencies : presonus::surface::SurfaceNetworkDependencies {
  int setups = 0;
  int mappingCount() const override { return 0; }
  const char *mappingName(int) const override { return "mapping"; }
  int kind(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  void title(const Presonus::UC::NetworkItem &,
             Core::CStringBuffer<128> &) const override {
    throw std::logic_error("unused");
  }
  const char *host(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  int targetType() const override { return 0; }
  bool stored(const char *, Presonus::UC::NetworkItem *) const override {
    throw std::logic_error("unused");
  }
  void acquire(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void release(Presonus::UC::NetworkItem *, bool) override {
    throw std::logic_error("unused");
  }
  void *component(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void *mixerCast(void *) override { throw std::logic_error("unused"); }
  void *dawCast(void *) override { throw std::logic_error("unused"); }
  void setMixer(void *) override { throw std::logic_error("unused"); }
  void setDAW(void *) override { throw std::logic_error("unused"); }
  void setTransport(void *) override { throw std::logic_error("unused"); }
  void itemInfo(int, Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void storeSelected(const char *, Presonus::UC::NetworkItem *, int) override {
    throw std::logic_error("unused");
  }
  void setNetworkRoot(Component *) override {
    throw std::logic_error("unused");
  }
  void selectModelItem(Presonus::UC::NetworkItem *) override { ++setups; }
  int wiredAssignMode() const override { throw std::logic_error("unused"); }
  void configureNetwork(const char *) override {
    throw std::logic_error("unused");
  }
  void resumeAdaptors() override { throw std::logic_error("unused"); }
  void enableNetwork(bool) override { throw std::logic_error("unused"); }
  void setupLocalIP() override { throw std::logic_error("unused"); }
};

const char *names[] = {nullptr,        "",          "RadioToggleButton",
                       "networkList",  "ListModel", "other",
                       "child/custom", "choice",    "child"};
struct Child : Component, ComponentViewController<Child> {
  int calls = 0;
  View sentinel;
  void *castTo(ITypedObject::TypeID id) override {
    if (id == ViewController::kTypeID)
      return static_cast<ViewController *>(this);
    return Component::castTo(id);
  }
  View *createView(const char *name) override {
    assert(std::strcmp(name, "custom") == 0);
    ++calls;
    return &sentinel;
  }
  void *getObjectForView(const char *name, const char *type) override {
    assert(std::strcmp(name, "custom") == 0);
    assert(std::strcmp(type, "Other") == 0);
    ++calls;
    return &sentinel;
  }
};
void providerRegression() {
  Parameters params;
  Param parameter;
  params.add(&parameter);
  Dependencies deps;
  presonus::surface::SurfaceNetworkProvider provider;
  Presonus::DelayTimer timer(0);
  presonus::surface::SurfaceNetworkState state{params, deps, provider, timer};
  auto holder =
      std::make_unique<Presonus::Surface::NetworkSetupComponent>(state);
  auto &component = *holder;
  auto *child = new Child;
  child->setName("child");
  component.addChild(child);
  assert(Core::Portable::core_cast<ViewController>(static_cast<Component *>(
             &component)) == static_cast<ViewController *>(&component));
  assert(component.getObjectForView("choice", "Param") == &parameter);
  assert(component.getObjectForView("child", "Controller") ==
         static_cast<ViewController *>(child));
  assert(component.createView("child/custom") == &child->sentinel);
  assert(component.getObjectForView("child/custom", "Other") ==
         &child->sentinel);
  assert(child->calls == 2);
  failNextAllocation = true;
  try {
    component.createView("RadioToggleButton");
    assert(false);
  } catch (const std::bad_alloc &) {
    assert(!failNextAllocation);
  }
  failNextAllocation = true;
  try {
    component.getObjectForView("networkList", "ListModel");
    assert(false);
  } catch (const std::bad_alloc &) {
    assert(!failNextAllocation && state.model == nullptr);
  }
  auto *model = static_cast<ListViewModel *>(
      component.getObjectForView("networkList", "ListModel"));
  assert(model == state.model && model->getItemCount() == 1 &&
         model->isSelectionHandler());
  assert(model->isItemSelected(0));
  ListView view(Core::Rect(0, 0, 120, 80), model);
  assert(view.getModel() == model);
  auto *typed =
      static_cast<Presonus::Surface::NetworkSetupComponent::ListModel *>(model);
  auto *identity =
      reinterpret_cast<Presonus::UC::NetworkItem *>(uintptr_t(0x1000));
  for (int i = 0; i < 20; ++i) {
    auto *row = new ListViewItem("row");
    if (i == 19)
      row->setUserData(identity);
    model->addItem(row);
  }
  model->changed();
  typed->setSelected(identity);
  assert(model->isItemSelected(20) && view.getScrollPosition() > 0);
  typed->setSelected(nullptr);
  assert(view.getScrollPosition() == 0);
  view.scrollTo(10);
  assert(view.getScrollPosition() > 0);
  component.setupListModel();
  assert(view.getScrollPosition() == 0);
  assert(deps.setups == 2 && model->getItemCount() == 1);
  view.setModel(nullptr);
  watched = model;
  frees = 0;
  holder.reset();
  assert(frees == 1 && state.model == nullptr);
  params.detach(&parameter);
}
} // namespace
extern "C" void *__real__Znwm(size_t);
extern "C" void *__wrap__Znwm(size_t size) {
  if (failNextAllocation) {
    failNextAllocation = false;
    throw std::bad_alloc();
  }
  return __real__Znwm(size);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched) {
    ++frees;
    watched = nullptr;
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, size_t n) {
  if (p == watched) {
    ++frees;
    watched = nullptr;
  }
  __real__ZdlPvm(p, n);
}
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  if (first) {
    assert(first->count() == 0 && second->count() == 0);
    ++detaches;
  }
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
extern "C" void radioD1(Presonus::Surface::RadioToggleButton *) asm(
    "_ZN8Presonus7Surface17RadioToggleButtonD1Ev");
int main() {
  providerRegression();
  int t, a, b, c, d;
  uint32_t v;
  while (std::cin >> t >> a >> b >> c >> d >> v) {
    events.clear();
    if (t == 3) {
      Param p;
      p.raw = number(v);
      Probe radio(Core::Rect(), a ? &p : nullptr, b, c);
      radio.setDown(d);
      p.capture = true;
      radio.push();
      p.capture = false;
      std::cout << radio.getDown() << ' ' << events.size();
      for (auto e : events)
        std::cout << ' ' << e.code << ' ' << e.value << ' ' << e.edit;
    } else if (t == 4 || t == 5) {
      Param p;
      BitmapProbe one, two;
      first = &one;
      second = a == 2 ? &one : &two;
      frees = detaches = 0;
      auto *radio = new Presonus::Surface::RadioToggleButton(Core::Rect(),
                                                             c ? &p : nullptr);
      if (a)
        radio->setImage(BitmapReference(first));
      if (b)
        radio->setIcon(BitmapReference(second));
      watched = radio;
      if (t == 4)
        delete radio;
      else
        radioD1(radio);
      std::cout << first->count() << ' ' << second->count() << ' ' << detaches
                << ' ' << frees;
      if (t == 5) {
        watched = nullptr;
        ::operator delete(radio);
      }
      first = second = nullptr;
    } else {
      Parameters params;
      Dependencies deps;
      presonus::surface::SurfaceNetworkProvider provider;
      Presonus::DelayTimer timer(0);
      presonus::surface::SurfaceNetworkState state{params, deps, provider,
                                                   timer};
      ListViewModel borrowed;
      if (c)
        state.model = &borrowed;
      {
        Presonus::Surface::NetworkSetupComponent component(state);
        if (t == 1) {
          View *view = component.createView(names[a]);
          bool special = view && Core::Portable::core_cast<RadioButton>(view);
          std::cout << int(special) << ' ' << int(view != nullptr) << " 0";
          if (special)
            assert(static_cast<Presonus::Surface::RadioToggleButton *>(view)
                       ->getOffValue() == 0);
          delete view;
        } else {
          const char *type = b == 0   ? nullptr
                             : b == 1 ? ""
                             : b == 2 ? "ListModel"
                                      : "Other";
          auto *result = component.getObjectForView(names[a], type);
          std::cout << int(result != nullptr) << ' ' << int(result && !c) << ' '
                    << deps.setups;
          if (result)
            assert(result == component.getObjectForView(names[a], type));
        }
      }
      if (!c)
        assert(state.model == nullptr);
      else
        assert(state.model == &borrowed);
    }
    std::cout << '\n';
  }
}
