#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Core::Portable::Component;
using Core::Portable::IStorageFilter;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::ParamObserverBase;
using Presonus::Mixer::MixerComponentBase;

namespace {
class Filter : public IStorageFilter {
public:
  Filter(Component &parent, std::string selection)
      : parent(parent), selection(std::move(selection)) {}
  void *castTo(TypeID) override { return nullptr; }
  bool shouldLoad(int type, const char *name, void *object) const override {
    const auto id = parent.getChildIndex(static_cast<Component *>(object));
    if (type != Component::kTypeID || id < 0 ||
        parent.getChild(id)->getName() != name)
      throw std::runtime_error("unexpected storage filter arguments");
    std::cout << 'f' << id << ':' << name << '\n';
    return selection.find(name) != std::string::npos;
  }
  bool shouldSave(int, const char *, void *) const override {
    throw std::runtime_error("unexpected save query");
  }

private:
  Component &parent;
  std::string selection;
};
class ResetObserver : public ParamObserverBase {
public:
  explicit ResetObserver(std::vector<Parameter *> &parameters)
      : parameters(parameters) {}
  void paramChanged(Parameter *parameter, int msg) override {
    if (msg != Parameter::kChanged)
      throw std::runtime_error("unexpected reset edit or range event");
    for (std::size_t i = 0; i < parameters.size(); ++i)
      if (parameters[i] == parameter)
        std::cout << 'r' << i << ":1:0\n";
  }

private:
  std::vector<Parameter *> &parameters;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string selection(argv[2]);
  const ParamInfo infos[] = {
      {ParamInfo::kFloat, 1, "stored", 0.f, 1.f, 0.f, .25f, 0.f,
       ParamInfo::kStorable, nullptr, nullptr, nullptr, nullptr, nullptr},
      {ParamInfo::kFloat, 2, "volatile", 0.f, 1.f, 0.f, .25f, 0.f, 0, nullptr,
       nullptr, nullptr, nullptr, nullptr}};
  Component parent;
  std::vector<Parameter *> parameters;
  ResetObserver observer(parameters);
  for (const char id : std::string(argv[1])) {
    const char name[] = {id, '\0'};
    auto *child = new Component(name);
    child->addParameters(infos, 2);
    parent.addChild(child);
    auto *parameter = child->getParameterByTag(1);
    parameters.push_back(parameter);
    parameter->setValue(.75f);
    child->getParameterByTag(2)->setValue(.75f);
    parameter->addObserver(&observer);
  }
  Filter filter(parent, selection);
  MixerComponentBase mixer;
  mixer.resetComponentParent = &parent;
  mixer.checkResetComponents(filter);
  bool matched = true;
  for (int i = 0; i < parent.countChildren(); ++i) {
    auto *child = parent.getChild(i);
    auto *parameter = parameters[i];
    parameter->removeObserver(&observer);
    const bool selected = selection.find(child->getName()) != std::string::npos;
    matched &= parameter->getValue() == (selected ? .25f : .75f);
    matched &= child->getParameterByTag(2)->getValue() == .75f;
  }
  return matched ? 0 : 1;
}
