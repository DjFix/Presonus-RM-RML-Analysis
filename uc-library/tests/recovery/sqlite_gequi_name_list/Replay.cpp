#include "presonus/mixer/GEQComponent.hpp"
#include "presonus/panel/GeqUIComponent.hpp"

#include <cassert>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using Core::Portable::Component;
using Core::Portable::IParamObserver;
using Core::Portable::ListParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::ParamValue;
using Presonus::Mixer::ChannelComponent;
using Presonus::Mixer::GEQComponent;
using Presonus::Panel::GeqUIComponent;

namespace {
const ParamInfo selectorInfo{ParamInfo::kList, 0, "Selector", 0, 0};
const ParamInfo linkedInfo{ParamInfo::kToggle, 32, "Link", 0, 1};

class ObservedList final : public ListParam {
public:
  ObservedList() : ListParam(selectorInfo) {}
  void setValue(ParamValue value, bool edit) override {
    lastValue = value;
    lastEdit = edit;
    ++sets;
    ListParam::setValue(value, edit);
  }

  ParamValue lastValue = 0;
  bool lastEdit = false;
  int sets = 0;
};

class Panel final : public GeqUIComponent {
public:
  explicit Panel(presonus::gequi_port::Dependencies &dependencies)
      : GeqUIComponent(dependencies), selector(new ObservedList) {
    paramList.add(selector);
  }

  ObservedList *selector;
};

class Roster final : public presonus::gequi_port::Dependencies {
public:
  explicit Roster(const std::string &links) {
    for (char link : links) {
      auto geq = std::make_unique<GEQComponent>(
          GEQComponent::SourcePortConstruction{});
      geq->addParameters(&linkedInfo, 1);
      geq->getParameterByTag(32)->setValue(link == '1' ? 1.0f : 0.0f);
      geqs.push_back(std::move(geq));
    }
  }

  int geqCount() const override { return static_cast<int>(geqs.size()); }
  GEQComponent *geqAt(int index) const override { return geqs.at(index).get(); }
  Component &parameters(GEQComponent *geq) override {
    for (int index = 0; index < geqCount(); ++index) {
      if (geqAt(index) == geq) {
        std::cout << "link " << index << '\n';
        return *geq;
      }
    }
    std::abort();
  }
  Component &parameters(ChannelComponent *) override { std::abort(); }
  int channelKind(ChannelComponent *) const override { std::abort(); }
  std::uint32_t channelIndex(ChannelComponent *) const override {
    std::abort();
  }
  Parameter &channelLink(ChannelComponent *) override { std::abort(); }
  ChannelComponent *assignedChannel(int) override { std::abort(); }
  bool linked(GEQComponent *) const override { std::abort(); }
  bool linkSlave(GEQComponent *) const override { std::abort(); }
  bool linked(ChannelComponent *) const override { std::abort(); }
  void flatten(GEQComponent *) override { std::abort(); }
  GEQComponent *geqController(IParamObserver *) override { return nullptr; }
  ChannelComponent *channelController(IParamObserver *) override {
    return nullptr;
  }
  bool channelUpdateLink(ChannelComponent *) const override { std::abort(); }
  void updateGeqNameList() override { std::abort(); }

private:
  std::vector<std::unique_ptr<GEQComponent>> geqs;
};
} // namespace

int main(int argc, char **argv) {
  assert(argc == 3);
  const std::string links = argv[1];
  const int selection = std::stoi(argv[2]);
  Roster roster(links);
  Panel panel(roster);
  auto &selector = *panel.selector;
  for (int index = 0; index <= selection; ++index)
    selector.appendString("stale");
  selector.setValue(static_cast<float>(selection), false);
  assert(selector.getValue() == static_cast<float>(selection));
  selector.sets = 0;

  panel.updateGeqNameList();

  assert(selector.sets > 0);
  for (int index = 0; index < selector.getStringCount(); ++index)
    std::cout << "label " << selector.getStringAt(index) << '\n';
  std::cout << "restore " << selector.lastValue << ' ' << selector.lastEdit
            << '\n';
  std::cout << "selected " << selector.getValue() << '\n';
}
