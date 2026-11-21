#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/surface/SoloPageComponent.hpp"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

using namespace Core::Portable;

namespace {
class Mixer final : public Presonus::MixerClientComponentBase {
public:
  using MixerClientComponentBase::MixerClientComponentBase;
  Component *getChannelGroup(Presonus::ChannelType type) const override {
    std::printf("group %d\n", int(type));
    return MixerClientComponentBase::getChannelGroup(type);
  }
};

struct Observe final : ParamObserverBase {
  bool edited = false;
  void paramChanged(Parameter *parameter, int message) override {
    if (message == Parameter::kEdit) {
      edited = true;
    } else if (message == Parameter::kChanged) {
      std::printf("%s %d\n", parameter->getName(), edited);
      edited = false;
    }
  }
};

ParamInfo description(int tag, const char *name) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.tag = tag;
  std::strncpy(info.name, name, sizeof(info.name) - 1);
  info.minValue = -1.f;
  info.maxValue = 1.f;
  info.defaultValue = 0.25f;
  return info;
}

void observe(Parameter &parameter, Observe &observer) {
  parameter.setController(&observer);
  parameter.addObserver(&observer);
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  const auto mode = std::atoi(argv[1]);
  const auto message = std::atoi(argv[2]);
  const auto tag = std::atoi(argv[3]);
  const auto input =
      static_cast<std::uint32_t>(std::strtoul(argv[4], nullptr, 10));
  float value;
  std::memcpy(&value, &input, sizeof(value));
  Observe observer;
  const ParamInfo lineInfo = description(14, "line");
  const ParamInfo auxInfo = description(14, "aux");
  const ParamInfo buttonInfo = description(tag, "button");
  Component groups;
  Mixer mixer(groups);
  Presonus::Surface::SoloPageComponent page;
  NumericParam button(buttonInfo);
  button.setValueFast(value);
  observe(button, observer);
  auto addGroup = [&](const char *name, const ParamInfo &info,
                      bool addMissing) {
    auto *group = new Component(name);
    groups.addChild(group);
    auto *channel = new Component;
    group->addChild(channel);
    channel->addParameters(&info, 1);
    auto *solo = channel->getParameterByTag(14);
    solo->setValue(0.75f);
    observe(*solo, observer);
    if (addMissing)
      group->addChild(new Component);
    return solo;
  };
  Parameter *line = nullptr;
  Parameter *aux = nullptr;
  if (mode == 2) {
    line = addGroup("line", lineInfo, true);
    aux = addGroup("aux", auxInfo, false);
    addGroup("main", lineInfo, false);
  }
  if (mode)
    page.bindMixerClient(mixer);
  if (message < 0)
    page.clearSolos();
  else
    page.paramChanged(&button, message);
  if (line && aux)
    std::printf("state %d %d\n", int(line->getValue() * 4.f),
                int(aux->getValue() * 4.f));
  if (message == 1 && tag == 100 && button.getValue() != 0.25f)
    return 3;
}
