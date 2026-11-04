#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
using Mixer = Presonus::Mixer::MixerComponentBase;
std::vector<std::string> events;
std::vector<std::uint32_t> writes;
bool capture = false;
class Tree final : public Component {
public:
  explicit Tree(const char *name) : Component(name) {}
  Component *findChild(const char *name) const override {
    if (capture)
      events.push_back("[\"lookup\",\"" + std::string(getName().str()) +
                       "\",\"" + name + "\"]");
    return Component::findChild(name);
  }
};
class Observer final : public Component {
public:
  Mixer &mixer;
  int channel, mutateAt, mutateCount;
  std::string kind;
  Observer(Mixer &m, int c, int at, int count, std::string kind)
      : mixer(m), channel(c), mutateAt(at), mutateCount(count), kind(kind) {}
  void paramChanged(Parameter *p, int msg) override {
    if (!capture)
      return;
    events.push_back("[\"" + kind + "\"," + std::to_string(channel) + "," +
                     std::to_string(p->getTag()) + "," + std::to_string(msg) +
                     "]");
    if (kind == "observer" && channel == mutateAt) {
      mixer.hardwareMicLineInputs = static_cast<std::uint32_t>(mutateCount);
      writes.push_back(mixer.hardwareMicLineInputs);
    }
  }
};
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--guards") {
    Mixer mixer;
    mixer.routeInputsToNet(); // Zero count does not require a root.
    mixer.hardwareMicLineInputs = 0xffffffffU;
    mixer.routeInputsToNet(); // Negative signed bound also does not.
    mixer.hardwareMicLineInputs = 1;
    int errors = 0;
    try {
      mixer.routeInputsToNet();
    } catch (const std::logic_error &) {
      ++errors;
    }
    Component root("root");
    auto *line = new Component("line");
    auto *channel = new Component("ch1");
    line->addChild(channel);
    root.addChild(line);
    mixer.routeInputParameters = &root;
    try {
      mixer.routeInputsToNet();
    } catch (const std::logic_error &) {
      ++errors;
    }
    std::cout << "{\"source_port_guards\":" << errors << "}" << std::endl;
    return errors == 2 ? 0 : 4;
  }
  if (argc != 7)
    return 2;
  Mixer mixer;
  mixer.hardwareMicLineInputs = static_cast<std::uint32_t>(std::stoll(argv[1]));
  const bool hasLine = std::atoi(argv[2]);
  const int mutateAt = std::atoi(argv[4]), mutateCount = std::atoi(argv[5]);
  const bool feedback = std::atoi(argv[6]);
  Tree root("root");
  mixer.routeInputParameters = &root;
  auto *line = new Tree("line");
  if (hasLine)
    root.addChild(line);
  std::vector<Observer *> observers, controllers;
  std::vector<Parameter *> parameters;
  const ParamInfo info[] = {
      PARAM_INT(0x130, "route", 0, 100, 7, nullptr, 0, 0, 0),
      PARAM_INT(0x131, "decoy", 0, 100, 11, nullptr, 0, 0, 0)};
  std::istringstream names(argv[3]);
  std::string item;
  while (std::getline(names, item, ',')) {
    if (item.empty())
      continue;
    const int index = std::stoi(item);
    auto *channel = new Component(("ch" + item).c_str());
    line->addChild(channel);
    channel->addParameters(info, 2);
    auto *p = channel->getParameterByTag(0x130);
    auto *o = new Observer(mixer, index, mutateAt, mutateCount, "observer");
    auto *c = new Observer(mixer, index, 0, 0, "controller");
    p->addObserver(o);
    if (feedback) {
      p->setController(c);
      p->setFeedbackNeeded(true);
    }
    observers.push_back(o);
    controllers.push_back(c);
    parameters.push_back(p);
  }
  capture = true;
  mixer.routeInputsToNet();
  capture = false;
  std::cout << "{\"events\":[";
  for (std::size_t i = 0; i < events.size(); ++i)
    std::cout << (i ? "," : "") << events[i];
  std::cout << "],\"count\":" << mixer.hardwareMicLineInputs
            << ",\"count_writes\":[";
  for (std::size_t i = 0; i < writes.size(); ++i)
    std::cout << (i ? "," : "") << writes[i];
  std::cout << "]}" << std::endl;
  for (std::size_t i = 0; i < parameters.size(); ++i) {
    if (parameters[i]->getValue() != 7.f ||
        line->findChild(("ch" + std::to_string(observers[i]->channel)).c_str())
                ->getParameterByTag(0x131)
                ->getValue() != 11.f)
      return 3;
    parameters[i]->removeObserver(observers[i]);
    parameters[i]->setController(nullptr);
    delete observers[i];
    delete controllers[i];
  }
  if (!hasLine)
    delete line;
}
