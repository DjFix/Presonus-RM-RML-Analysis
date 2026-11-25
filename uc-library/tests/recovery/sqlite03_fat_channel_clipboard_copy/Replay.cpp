#include "core/portable/corecomponent.h"
#include "presonus/surface/FatChannelClipboard.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using Core::Portable::Component;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Surface::FatChannelClipboard;

using Trace = std::vector<std::string>;

struct Watch : Core::Portable::IParamObserver {
  Watch(int id, Trace &trace) : id(id), trace(trace) {}
  void *castTo(TypeID type) override {
    return type == kTypeID ? static_cast<IParamObserver *>(this) : nullptr;
  }
  void paramChanged(Parameter *, int message) override {
    trace.push_back("changed:" + std::to_string(id) + ":" +
                    std::to_string(message));
  }
  int id;
  Trace &trace;
};

struct Selection : NumericParam {
  Selection(const ParamInfo &info, int id, Trace &trace)
      : NumericParam(info), id(id), trace(trace), watch(id, trace) {
    addObserver(&watch);
  }
  ~Selection() { removeObserver(&watch); }

  void resetValue(bool edit) override {
    trace.push_back("reset:" + std::to_string(id) + ":" + std::to_string(edit));
    NumericParam::resetValue(edit);
  }
  float getValue() const override {
    trace.push_back("value:" + std::to_string(id));
    return NumericParam::getValue();
  }
  int id;
  Trace &trace;
  Watch watch;
};

struct FixtureComponent : Component {
  ~FixtureComponent() { children.removeAll(); }
  void addBorrowed(Component *child) { children.add(child); }
  void addSelection(Selection *selection) { paramList.add(selection); }
};

int readInt() {
  int value = 0;
  std::cin >> value;
  return value;
}
template <typename To, typename From> To bitCopy(From source) {
  static_assert(sizeof(To) == sizeof(From));
  To result;
  std::memcpy(&result, &source, sizeof(result));
  return result;
}
float readFloat() {
  std::uint32_t value = 0;
  std::cin >> value;
  return bitCopy<float>(value);
}
void printTrace(const Trace &trace) {
  for (const auto &event : trace)
    std::cout << ' ' << event;
  std::cout << std::endl;
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string mode = argv[1];
  Trace trace;
  const int size = readInt();
  std::vector<ParamInfo> infos(size + 1);
  std::vector<std::unique_ptr<FixtureComponent>> components(size + 1);
  std::vector<Selection *> params(size + 1);
  for (int id = 1; id <= size; ++id) {
    auto &info = infos.at(id);
    auto &component = components.at(id);
    component = std::make_unique<FixtureComponent>();
    info.type = ParamInfo::kFloat;
    info.tag = readInt();
    info.minValue = -100.f;
    info.maxValue = 100.f;
    info.defaultValue = readFloat();
    const auto value = readFloat();
    if (info.tag) {
      auto *param = new Selection(info, id, trace);
      component->addSelection(param);
      param->setValue(value);
      params.at(id) = param;
    }
  }
  trace.clear();
  FatChannelClipboard clipboard;
  const int prior = readInt();
  clipboard.copy(components.at(prior).get());
  const int source = readInt();
  const int groupCount = readInt();
  std::vector<std::unique_ptr<FixtureComponent>> groups;
  for (int group = 0; group < groupCount; ++group) {
    auto component = std::make_unique<FixtureComponent>();
    const int count = readInt();
    for (int index = 0; index < count; ++index)
      component->addBorrowed(components.at(readInt()).get());
    clipboard.portableRoster().add(component.get());
    groups.push_back(std::move(component));
  }
  const int capacity = readInt();
  Core::Vector<Component *> output(capacity, 5);
  const int existing = readInt();
  for (int index = 0; index < existing; ++index)
    output.add(components.at(readInt()).get());

  const auto componentID = [&](const Component *component) {
    for (std::size_t id = 0; id < components.size(); ++id)
      if (components.at(id).get() == component)
        return static_cast<int>(id);
    return -1;
  };
  const auto printValues = [&] {
    for (std::size_t id = 1; id < params.size(); ++id)
      if (const auto *param = params.at(id))
        std::cout << ' ' << id << ':'
                  << bitCopy<std::uint32_t>(param->NumericParam::getValue());
  };

  if (mode == "provider") {
    std::string command;
    while (std::cin >> command) {
      if (command == "tag") {
        const auto id = readInt();
        const auto tag = readInt();
        const auto *found = components.at(id)->getParameterByTag(tag);
        std::cout << (found == params.at(id) && found ? id : 0) << std::endl;
      } else if (command == "reset") {
        const auto id = readInt();
        const bool edit = readInt() != 0;
        static_cast<Parameter *>(params.at(id))->resetValue(edit);
        printTrace(trace);
        trace.clear();
      } else if (command == "value") {
        const auto id = readInt();
        const auto value = static_cast<Parameter *>(params.at(id))->getValue();
        std::cout << bitCopy<std::uint32_t>(value);
        printTrace(trace);
        trace.clear();
      } else if (command == "resize") {
        const bool resized = output.resize(readInt());
        std::cout << resized << ' ' << output.getCapacity() << std::endl;
      } else if (command == "capacity") {
        std::cout << output.getCapacity() << std::endl;
      } else if (command == "values") {
        printValues();
        std::cout << std::endl;
      } else {
        return 3;
      }
    }
  } else if (mode == "copy") {
    clipboard.copy(components.at(source).get());
    std::cout << componentID(clipboard.portableSource());
    printValues();
    printTrace(trace);
  } else if (mode == "collectpastechannels") {
    clipboard.collectPasteChannels(output);
    for (int index = 0; index < output.count(); ++index)
      std::cout << ' ' << componentID(output.at(index));
    std::cout << " |";
    printTrace(trace);
  } else {
    return 4;
  }
}
