#include "presonus/DAWChannelGroup.hpp"

#include <cassert>
#include <iostream>
#include <string_view>

using Core::Portable::Component;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::ParamObserverBase;

namespace {
class ChannelGroupProbe : public Presonus::DAWChannelGroup {
public:
  void bind(Parameter &parameter) { cachedParameter_ = &parameter; }
};

class Observer : public ParamObserverBase {
public:
  void paramChanged(Parameter *parameter, int message) override {
    assert(parameter == expected);
    if (message == Parameter::kChanged)
      ++changes;
    else if (message == Parameter::kEdit)
      ++edits;
    else
      assert(false);
  }

  Parameter *expected{};
  int changes{};
  int edits{};
};
} // namespace

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string_view mode = argv[1];
  assert(mode == "get" || mode == "reset");
  float initialValue;
  int children;
  while (std::cin >> initialValue >> children) {
    const ParamInfo info =
        PARAM_FLOAT(6, "used", -20, 20, 7, 0, nullptr, nullptr, 0, 0);
    ChannelGroupProbe group;
    for (int index = 0; index < children; ++index)
      group.addChild(new Component);
    Observer observer;
    NumericParam parameter(info);
    parameter.setValue(initialValue, false);
    assert(parameter.getValue() == initialValue);
    observer.expected = &parameter;
    parameter.setController(&observer);
    parameter.addObserver(&observer);
    group.bind(parameter);
    if (mode == "get") {
      const Presonus::DAWChannelGroup &constGroup = group;
      std::cout << constGroup.getUsedCount() << '\n';
      assert(parameter.getValue() == initialValue);
      assert(observer.changes == 0 && observer.edits == 0);
    } else {
      group.resetUsedCount();
      std::cout << parameter.getValue() << ' ' << observer.changes << ' '
                << observer.edits << '\n';
    }
    assert(group.countChildren() == children);
    parameter.removeObserver(&observer);
    parameter.setController(nullptr);
  }
  assert(std::cin.eof());
}
