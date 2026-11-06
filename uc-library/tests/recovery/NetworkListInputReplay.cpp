#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include <cassert>
#include <iostream>
#include <memory>
#include <vector>
using namespace Core::Portable;
using Owner = Presonus::Surface::NetworkSetupComponent;
std::vector<int> events;
bool capture = false;
Presonus::UC::NetworkItem *identity = nullptr;
int forcedType = -1;
ListViewItem *mutatedRow = nullptr;
struct Dependencies : presonus::surface::SurfaceNetworkDependencies {
  int kind(const Presonus::UC::NetworkItem &) const override { return {}; }
  Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &) const override {
    return {};
  }
  void title(const Presonus::UC::NetworkItem &,
             Core::CStringBuffer<128> &) const override {}
  const char *host(const Presonus::UC::NetworkItem &) const override {
    return {};
  }
  int mappingCount() const override { return {}; }
  const char *mappingName(int) const override { return {}; }
  int targetType() const override { return {}; }
  bool stored(const char *, Presonus::UC::NetworkItem *) const override {
    return {};
  }
  void acquire(Presonus::UC::NetworkItem *) override {}
  void release(Presonus::UC::NetworkItem *, bool) override {}
  void *component(Presonus::UC::NetworkItem *) override { return nullptr; }
  void *mixerCast(void *) override { return nullptr; }
  void *dawCast(void *) override { return nullptr; }
  void setMixer(void *) override {}
  void setDAW(void *) override {}
  void setTransport(void *) override {}
  void itemInfo(int, Presonus::UC::NetworkItem *) override {}
  void storeSelected(const char *, Presonus::UC::NetworkItem *, int) override {}
  void setNetworkRoot(Core::Portable::Component *) override {}
  void selectModelItem(Presonus::UC::NetworkItem *) override {}
  int wiredAssignMode() const override { return {}; }
  void configureNetwork(const char *) override {}
  void resumeAdaptors() override {}
  void enableNetwork(bool) override {}
  void setupLocalIP() override {}
};

struct Params : Component {
  void add(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct Model : Owner::ListModel {
  using ListModel::ListModel;
  void nullEntry() { items.add(nullptr); }
};
struct Probe : ListView {
  int id;
  const WheelEvent *expected = nullptr;
  Probe(int i, Model &m) : ListView(Core::Rect(0, 0, 100, 80), &m), id(i) {}
  bool onWheelInput(const WheelEvent &e) override {
    assert(&e == expected);
    events.push_back(id);
    return id % 2;
  }
  void invalidate(Core::RectRef) override {
    if (capture)
      events.push_back(40);
  }
};
extern "C" int realTarget(const Owner *) asm(
    "__real__ZNK8Presonus7Surface21NetworkSetupComponent13getTargetTypeEv");
extern "C" int wrapTarget(const Owner *p) asm(
    "__wrap__ZNK8Presonus7Surface21NetworkSetupComponent13getTargetTypeEv");
extern "C" int wrapTarget(const Owner *p) {
  if (capture) {
    events.push_back(10);
    // Changes after original userData load must not affect the selected
    // identity.
    if (mutatedRow)
      mutatedRow->setUserData(nullptr);
  }
  return forcedType >= 0 ? forcedType : realTarget(p);
}
extern "C" void realMixer(Owner *, Presonus::UC::NetworkItem *, int) asm(
    "__real__ZN8Presonus7Surface21NetworkSetupComponent11selectMixerEPNS_"
    "2UC11NetworkItemEi");
extern "C" void wrapMixer(Owner *, Presonus::UC::NetworkItem *, int) asm(
    "__wrap__ZN8Presonus7Surface21NetworkSetupComponent11selectMixerEPNS_"
    "2UC11NetworkItemEi");
extern "C" void wrapMixer(Owner *p, Presonus::UC::NetworkItem *i, int f) {
  if (capture) {
    events.push_back(20);
    events.push_back(i == identity ? 1 : 0);
    events.push_back(f);
  }
  realMixer(p, i, f);
}
extern "C" void realDAW(Owner *, Presonus::UC::NetworkItem *, int) asm(
    "__real__ZN8Presonus7Surface21NetworkSetupComponent9selectDAWEPNS_"
    "2UC11NetworkItemEi");
extern "C" void wrapDAW(Owner *, Presonus::UC::NetworkItem *, int) asm(
    "__wrap__ZN8Presonus7Surface21NetworkSetupComponent9selectDAWEPNS_"
    "2UC11NetworkItemEi");
extern "C" void wrapDAW(Owner *p, Presonus::UC::NetworkItem *i, int f) {
  if (capture) {
    events.push_back(30);
    events.push_back(i == identity ? 1 : 0);
    events.push_back(f);
  }
  realDAW(p, i, f);
}
int main() {
  int mode, a, b, c, d, e;
  while (std::cin >> mode >> a >> b >> c >> d >> e) {
    Params params;
    const ParamInfo info =
        PARAM_FLOAT(30, "target", 0, 10, 0, 0, nullptr, nullptr, 0, 0);
    NumericParam target(info);
    params.add(&target);
    target.setValue(float(c), false);
    Dependencies deps;
    presonus::surface::SurfaceNetworkProvider network;
    Presonus::DelayTimer timer(0);
    presonus::surface::SurfaceNetworkState state{params, deps, network, timer};
    {
      Owner owner(state);
      Model model(&owner);
      Presonus::UC::NetworkItem item(nullptr);
      identity = d ? &item : nullptr;
      if (mode == 0) {
        WheelEvent event(b, WheelEvent::Axis(c));
        std::vector<std::unique_ptr<Probe>> views;
        for (int i = 0; i < a; ++i) {
          views.emplace_back(new Probe(i + 1, model));
          views.back()->expected = &event;
        }
        events.clear();
        model.onWheelInput(event);
        for (auto &v : views)
          v->setModel(nullptr);
        model.onWheelInput(event);
        assert(int(events.size()) == a);
        // Actual unmodified ListView uses inherited View::onWheelInput,
        // returning false.
        ListView actual(Core::Rect(), &model);
        assert(!actual.onWheelInput(event));
        actual.setModel(nullptr);
      } else {
        if (e == 0)
          model.nullEntry();
        else {
          auto *row = new ListViewItem("row");
          row->setUserData(identity);
          mutatedRow = row;
          model.addItem(row);
        }
        Probe view(1, model);
        forcedType = c > 1 ? c : -1;
        events.clear();
        capture = true;
        model.selectListItem(a, b, &view, e);
        capture = false;
        mutatedRow = nullptr;
        view.setModel(nullptr);
        forcedType = -1;
      }
      for (size_t i = 0; i < events.size(); ++i)
        std::cout << (i ? " " : "") << events[i];
      std::cout << '\n';
    }
    params.detach(&target);
  }
}
