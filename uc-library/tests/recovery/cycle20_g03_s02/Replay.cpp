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
  const PageComponent *current = nullptr;
  mutable int probes = 0;
  void *castOwner(void *owner, int) const override { return owner; }
  const void *currentPage(void *) const override {
    ++probes;
    return current;
  }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};

struct Observer final : GeqPageComponent::IObserver {
  Observer(GeqPageComponent &page, Bindings &bindings)
      : page(page), bindings(bindings) {}
  void onGeqScrollOffsetChanged() override {
    char label[64]{};
    PageObserverAccess::bandParameters(page).byTag(0)->toString(label, 64);
    std::cout << "observer " << PageObserverAccess::notifiedOffset(page) << ' '
              << bindings.probes << ' ' << label << ' ';
  }
  GeqPageComponent &page;
  Bindings &bindings;
};

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  Bindings bindings;
  PageComponent visibility(&bindings, bindings, "geq");
  GeqPageComponent geq;
  auto &bands = PageObserverAccess::bandParameters(geq);
  auto &component = PageObserverAccess::geqComponent(geq);
  const ParamInfo target = PARAM_TOGGLE(71, "band_gain_01", 0, 0, 0);
  component.addParameters(&target, 1, true);
  for (int row = 0; row < 16; ++row) {
    const ParamInfo label = PARAM_STRING(2 * row, "label", 0);
    bands.add(label, true);
    bands.byTag(2 * row)->fromString("old", false);
    bands.addAlias(2 * row + 1, "alias");
  }
  PageObserverAccess::bindGeqPage(geq, visibility);
  const int notified = std::atoi(argv[4]);
  if (notified != 0) {
    bindings.current = &visibility;
    PageObserverAccess::listOffset(geq) = notified;
    geq.updateBands();
    bands.byTag(0)->fromString("old", false);
    bindings.probes = 0;
  }
  PageObserverAccess::listOffset(geq) = std::atoi(argv[3]);
  bindings.current = std::atoi(argv[2]) ? &visibility : nullptr;
  Observer observer(geq, bindings);
  PageObserverAccess::observers(geq).add(&observer);
  geq.onShow(std::atoi(argv[1]));
  geq.updateBands(); // A normal refresh at the same offset is silent.
  char label[64]{};
  bands.byTag(0)->toString(label, 64);
  auto *alias = bands.getAlias(1)->getOriginal();
  std::cout << PageObserverAccess::listOffset(geq) << ' '
            << PageObserverAccess::notifiedOffset(geq) << ' ' << bindings.probes
            << ' ' << label << ' ' << (alias ? alias->getTag() : 0) << '\n';
}
