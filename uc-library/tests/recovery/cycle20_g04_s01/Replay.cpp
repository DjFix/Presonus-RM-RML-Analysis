#include "presonus/mixer/FilterGroupManager.hpp"
#include "presonus/uc/message_attributes.hpp"
#include <algorithm>
#include <array>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using Core::Portable::Component;
using Core::Portable::Parameter;
using Presonus::Mixer::FilterGroupManager;

namespace {
constexpr std::array names{"ch1", "fixed", "ch30", "ch4"};
constexpr Core::Portable::ParamInfo parameters[] = {
    PARAM_TOGGLE(0, "a", 0, nullptr, 0),
    PARAM_TOGGLE(1, "b", 0, nullptr, 0),
};

std::string snapshot(const FilterGroupManager &manager,
                     const std::array<Component *, names.size()> &children) {
  if (manager.countChildren() != static_cast<int>(children.size()))
    return "invalid child count";
  std::ostringstream result;
  for (int i = 0; i < manager.countChildren(); ++i) {
    const auto *child = manager.getChild(i);
    const auto found = std::find(children.begin(), children.end(), child);
    if (found == children.end() || child->getParent() != &manager)
      return "invalid child or parent";
    if (i)
      result << ',';
    result << (found - children.begin()) << ':' << child->getName();
  }
  return result.str();
}

class Observer final : public Core::Portable::ParamObserverBase {
public:
  Observer(const FilterGroupManager &manager,
           const std::array<Component *, names.size()> &children)
      : manager(manager), children(children) {}

  void paramChanged(Parameter *parameter, int message) override {
    if (message != Parameter::kChanged)
      return;
    for (std::size_t i = 0; i < children.size(); ++i) {
      for (int j = 0; j < children[i]->countParameters(); ++j) {
        if (children[i]->getParameterAt(j) == parameter) {
          events.push_back(std::to_string(i) + ":" + std::to_string(j) + ":" +
                           snapshot(manager, children));
          return;
        }
      }
    }
    events.emplace_back("unrecognized parameter");
  }

  std::vector<std::string> events;

private:
  const FilterGroupManager &manager;
  const std::array<Component *, names.size()> &children;
};
} // namespace

int main() {
  bool hasID;
  std::string id;
  int oldIndex;
  int newIndex;
  while (std::cin >> hasID >> std::quoted(id) >> oldIndex >> newIndex) {
    FilterGroupManager manager("filter-group");
    std::array<Component *, names.size()> children{};
    Observer observer(manager, children);
    for (std::size_t i = 0; i < children.size(); ++i) {
      auto *child = new Component(names[i]);
      children[i] = child;
      child->addParameters(parameters, 2);
      for (int j = 0; j < child->countParameters(); ++j)
        child->getParameterAt(j)->addObserver(&observer);
      manager.addChild(child);
    }
    Presonus::UC::MessageAttributes message(hasID ? id.c_str() : nullptr);
    message.set("ReorderOldIndex", static_cast<Core::int64>(oldIndex));
    message.set("ReorderNewIndex", static_cast<Core::int64>(newIndex));
    manager.notify(message);
    std::cout << snapshot(manager, children);
    for (const auto &event : observer.events)
      std::cout << '|' << event;
    std::cout << '\n';
    for (auto *child : children)
      for (int j = 0; j < child->countParameters(); ++j)
        child->getParameterAt(j)->removeObserver(&observer);
  }
  return std::cin.eof() ? 0 : 1;
}
