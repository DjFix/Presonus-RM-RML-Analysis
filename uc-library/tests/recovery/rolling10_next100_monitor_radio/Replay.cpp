#include "presonus/surface/MonitorPageComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <vector>
struct Tree : Core::Portable::Component {
  void attach(Core::Portable::Parameter *p) { paramList.add(p); }
  void detach(Core::Portable::Parameter *p) { paramList.remove(p); }
};
struct Observer : Core::Portable::Component {
  std::vector<std::pair<int, int>> events;
  std::vector<Core::Portable::Parameter *> *objects;
  void paramChanged(Core::Portable::Parameter *p, int msg) override {
    for (int i = 0; i < int(objects->size()); ++i)
      if ((*objects)[i] == p) {
        events.emplace_back(i, msg);
        return;
      }
    std::abort();
  }
};
int main(int argc, char **argv) {
  const bool direct = argc > 1;
  const bool probe = argc > 1 && std::strcmp(argv[1], "--lookup") == 0;
  int selected, first, last, n, calls, variant;
  while (std::cin >> selected >> first >> last >> n >> calls >> variant) {
    Tree tree;
    std::vector<Core::Portable::ParamInfo> infos(n);
    std::vector<std::unique_ptr<Core::Portable::NumericParam>> parameters;
    std::vector<Core::Portable::Parameter *> identities;
    Observer observer;
    observer.objects = &identities;
    for (int i = 0, tag; i < n; ++i) {
      std::cin >> tag;
      const Core::Portable::ParamInfo info =
          PARAM_FLOAT(tag, "radio", 0, 1, 0, 0, nullptr, nullptr, 0, 0);
      infos[i] = info;
      parameters.push_back(
          std::make_unique<Core::Portable::NumericParam>(infos[i]));
      parameters.back()->setValue(variant ? 1.f : 0.f, false);
      identities.push_back(parameters.back().get());
      tree.attach(parameters.back().get());
      parameters.back()->addObserver(&observer);
      parameters.back()->setController(&observer);
      parameters.back()->setFeedbackNeeded(true);
    }
    const Core::Portable::ParamInfo si =
        PARAM_FLOAT(selected, "selected", 0, 1, 0, 0, nullptr, nullptr, 0, 0);
    Core::Portable::NumericParam choice(si);
    Presonus::Surface::MonitorPageComponent page(
        Presonus::Surface::MonitorPageComponent::SourcePortConstruction{},
        tree);
    if (probe) {
      // Actual CCL registry observation only; no reconstructed method call.
    } else if (direct) {
      for (int i = 0; i < calls; ++i) {
        int identity, edit;
        unsigned bits;
        std::cin >> identity >> bits >> edit;
        float v;
        std::memcpy(&v, &bits, 4);
        parameters[identity]->setValue(v, edit);
      }
    } else
      page.radioSelection(&choice, first, last);
    std::cout << n;
    for (auto &p : parameters)
      std::cout << ' ' << p->getValue();
    std::cout << ' ' << observer.events.size();
    for (auto [i, msg] : observer.events)
      std::cout << ' ' << i << ' ' << msg;
    // Separate actual lookup observation establishes sparse/duplicate
    // semantics.
    if (first <= last && first >= -3 && last <= 4) {
      std::cout << ' ' << (last - first + 1);
      for (int tag = first; tag <= last; ++tag) {
        auto *p = tree.getParameterByTag(tag);
        int index = -1;
        for (int i = 0; i < n; ++i)
          if (identities[i] == p) {
            index = i;
            break;
          }
        std::cout << ' ' << index;
      }
    } else
      std::cout << " 0";
    std::cout << '\n';
    for (auto &p : parameters) {
      p->removeObserver(&observer);
      p->setController(nullptr);
      tree.detach(p.get());
    }
  }
}
