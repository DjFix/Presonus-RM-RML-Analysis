#include "core/portable/gui/coreview.h"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <iostream>
#include <vector>

using namespace Core::Portable;
using namespace Presonus;
using namespace Presonus::Surface;
using presonus::surface::PageObserverAccess;

struct Bindings final : presonus::page::Bindings {
  const PageComponent *page = nullptr;
  mutable int probes = 0;
  void *castOwner(void *owner, int) const override { return owner; }
  const void *currentPage(void *) const override {
    ++probes;
    return page;
  }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};

struct Observer final : GeqPageComponent::IObserver {
  Observer(std::vector<int> &events, int id) : events(events), id(id) {}
  void onGeqScrollOffsetChanged() override { events.push_back(id); }
  std::vector<int> &events;
  int id;
};

int main(int argc, char **argv) {
  if (argc < 4)
    return 2;
  const int method = std::atoi(argv[1]);
  Bindings bindings;
  PageComponent visibility(&bindings, bindings, "page");
  GeqPageComponent geq;
  PageObserverAccess::bindGeqPage(geq, visibility);
  PageObserverAccess::listOffset(geq) = std::atoi(argv[2]);
  std::vector<int> events;
  Observer first(events, 0), second(events, 1);
  auto &observers = PageObserverAccess::observers(geq);

  if (method == 4) {
    if (argc != 5)
      return 2;
    const bool visible = std::atoi(argv[4]);
    const int notified = std::atoi(argv[3]);
    auto &local = PageObserverAccess::bandParameters(geq);
    auto &component = PageObserverAccess::geqComponent(geq);
    for (int index = 1; index < 32; index += 2) {
      ParamInfo target = PARAM_TOGGLE(index, "", 0, 0, 0);
      Core::CString32 name;
      name.appendFormat("band_gain_%02d", index);
      Core::ConstString(name).copyTo(target.name, ParamInfo::kMaxNameLength);
      component.addParameters(&target, 1, true);
    }
    for (int row = 0; row < 16; ++row) {
      const ParamInfo label = PARAM_STRING(2 * row, "label", 0);
      local.add(label, true);
      local.addAlias(2 * row + 1, "alias");
    }
    if (notified != 0) {
      bindings.page = &visibility;
      PageObserverAccess::listOffset(geq) = notified;
      geq.updateBands();
      PageObserverAccess::listOffset(geq) = std::atoi(argv[2]);
      bindings.probes = 0;
      for (int row = 0; row < 16; ++row) {
        local.byTag(2 * row)->fromString("", false);
        local.getAlias(2 * row + 1)->setOriginal(nullptr);
      }
    }
    bindings.page = visible ? &visibility : nullptr;
    observers.add(&first);
    observers.add(&second);
    geq.updateBands();
    std::cout << PageObserverAccess::listOffset(geq) << ' '
              << PageObserverAccess::notifiedOffset(geq) << ' '
              << bindings.probes << '\n';
    for (int id : events)
      std::cout << id << ' ';
    std::cout << '\n';
    for (int row = 0; row < 16; ++row) {
      char text[64]{};
      local.byTag(2 * row)->toString(text, sizeof(text));
      auto *original = local.getAlias(2 * row + 1)->getOriginal();
      std::cout << text << ' ' << (original ? original->getTag() : 0) << '\n';
    }
    return 0;
  }

  if (method == 5) {
    geq.addListOffset(std::atoi(argv[3]));
  } else if (method == 6) {
    const WheelEvent event(std::atoi(argv[3]), WheelEvent::kVertical);
    geq.onWheelInput(event);
  } else if (method == 7 && argc == 6) {
    const ParamInfo info = PARAM_FLOAT(std::atoi(argv[3]), "scroll", -1, 1, 0,
                                       0.01f, 0, 0, 0, ParamInfo::kStorable);
    auto &component = PageObserverAccess::geqComponent(geq);
    component.addParameters(&info, 1);
    auto *parameter = component.getParameterAt(0);
    parameter->setValue(std::strtof(argv[5], nullptr), false);
    geq.paramChanged(parameter, std::atoi(argv[4]));
    std::cout << component.needsSave() << ' ';
  } else {
    return 2;
  }
  std::cout << PageObserverAccess::listOffset(geq) << ' ' << bindings.probes
            << '\n';
}
