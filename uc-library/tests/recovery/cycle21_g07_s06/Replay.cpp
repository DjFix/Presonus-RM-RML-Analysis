#include "presonus/mixer/MonoBusComponent.hpp"

#include <cstdio>
#include <cstdlib>
#include <vector>

using namespace Core::Portable;
using namespace Presonus::Mixer;
using presonus::send_output_port::SendState;

namespace {
ParamInfo description(ParamType type, int tag) {
  ParamInfo info{};
  info.type = type;
  info.tag = tag;
  info.maxValue = 4.f;
  return info;
}

class RangeAlias final : public AliasParam {
public:
  using AliasParam::AliasParam;
  int resets = 0;

  void resetValue(bool edit) override {
    if (!edit)
      std::abort();
    ++resets;
    AliasParam::resetValue(edit);
  }
};

class NameObserver final : public ParamObserverBase {
public:
  void paramChanged(Parameter *parameter, int message) override {
    if (message == Parameter::kChanged)
      std::printf("name %d %s\n", parameter->getTag(),
                  StringParam::cast(parameter)->getText().str());
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 7)
    return 2;
  const int message = std::atoi(argv[1]);
  const int tag = std::atoi(argv[2]);
  const bool positive = std::atoi(argv[3]) != 0;
  const bool modeEnabled = std::atoi(argv[4]) != 0;
  const bool updateNames = std::atoi(argv[5]) != 0;
  const bool available = std::atoi(argv[6]) != 0;

  const int nameTags[] = {0, 1, 2};
  const ParamInfo own[] = {
      description(ParamInfo::kString, 0), description(ParamInfo::kString, 1),
      description(ParamInfo::kString, 2), description(ParamInfo::kFloat, 411)};
  const ParamInfo split[] = {description(ParamInfo::kFloat, 258),
                             description(ParamInfo::kFloat, 259)};
  const auto aliasInfo = description(ParamInfo::kAlias, 88);
  const auto rangeInfo = description(ParamInfo::kFloat, 87);
  const auto triggerInfo = description(ParamInfo::kFloat, tag);
  NumericParam trigger(triggerInfo);
  trigger.setValue(positive ? 1.f : 0.f);
  NumericParam underlying(rangeInfo);
  underlying.setDefault(3.f);
  underlying.setValue(4.f);
  RangeAlias alias(aliasInfo);
  alias.setOriginal(&underlying);
  NameObserver nameObserver;
  presonus::mixer::ChannelState ownChannel, a, b, c;
  presonus::output_port::Bindings ownOutput{ownChannel};
  ownOutput.channelParamChanged = [&](Parameter *param, int reason) {
    if (param != &trigger || reason != message)
      std::abort();
    std::printf("send %d %d\n", param->getTag(), reason);
  };
  presonus::output_port::Bindings outA{a}, outB{b}, outC{c};
  SendState ownSend{ownOutput}, sendA{outA}, sendB{outB}, sendC{outC};
  OutputComponent output(ownOutput);
  std::vector<SendState *> normalSendChildren;
  SendOutputComponent send(output, ownSend, normalSendChildren);
  MonoBusComponent bus(ChannelComponent::SourcePortConstruction{});
  bus.addParameters(own, 4);
  for (int nameTag : nameTags) {
    auto *name = bus.getParameterByTag(nameTag);
    name->fromString("old");
    name->setController(nullptr);
    name->addObserver(&nameObserver);
  }
  bus.getParameterByTag(411)->setValue(modeEnabled ? 1.f : 0.f);
  Component channel;
  if (available) {
    channel.addParameters(split, 2);
    channel.getParameterByTag(259)->setValue(0.25f);
  }
  Core::Vector<Component *> channels;
  channels.add(&channel);
  Core::Vector<SendState *> first, second, third;
  first.add(&sendA);
  second.add(&sendB);
  third.add(&sendC);
  presonus::mono_bus_port::Bindings bindings{
      send,     ownSend,
      channels, {&first, &second, &third},
      "Aux",    available ? &alias : nullptr,
      2,        updateNames};
  bus.bindMonoBus(bindings);
  bus.paramChanged(&trigger, message);
  std::printf("dirty %u %d", ownSend.sendChanged, ownOutput.updatePending);
  for (auto *remote : {&sendA, &sendB, &sendC})
    std::printf(" %u %d", remote->childChanged, remote->output.updatePending);
  std::puts("");
  std::printf("splits %.2f %.2f\n",
              available ? channel.getParameterByTag(258)->getValue() : 0.f,
              available ? channel.getParameterByTag(259)->getValue() : 0.25f);
  for (int nameTag : nameTags)
    std::printf(
        "value %s\n",
        StringParam::cast(bus.getParameterByTag(nameTag))->getText().str());
  std::printf("alias %.0f %d\n", alias.getMin(), alias.resets);
  if (alias.resets && underlying.getValue() != 3.f)
    return 3;
}
