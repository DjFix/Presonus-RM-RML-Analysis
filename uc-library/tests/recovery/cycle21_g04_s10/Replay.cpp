#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/mixer/AliasMapping.hpp"
#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
namespace {
class AliasOwner : public Component {
public:
  AliasParam *createAlias() {
    return AliasParam::cast(paramList.addAlias(3, "alias"));
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int mode = std::atoi(argv[1]);
  const bool priorEnabled = std::atoi(argv[2]);
  const bool priorExists = std::atoi(argv[3]);
  static const ParamInfo foundInfo =
      PARAM_INT(4, "gain", 0, 9, 2, nullptr, nullptr, 0, 0);
  static const ParamInfo fallbackInfo =
      PARAM_INT(5, "fallback", 0, 9, 2, nullptr, nullptr, 0, 0);
  static const ParamInfo previousInfo =
      PARAM_INT(6, "previous", 0, 9, 2, nullptr, nullptr, 0, 0);
  NumericParam fallback(fallbackInfo);
  NumericParam previous(previousInfo);
  previous.enable(priorEnabled);
  Component root;
  auto *channel = new Component("channel");
  root.addChild(channel);
  channel->addParameters(&foundInfo, 1);
  auto *found = channel->getParameterByTag(4);
  Presonus::MixerClientComponentBase mixer;
  AliasOwner owner;
  auto *alias = owner.createAlias();
  alias->setOriginal(priorExists ? &previous : nullptr);
  Presonus::Mixer::AliasMapping mapping(
      alias, &fallback, mode == 2 ? "missing/gain" : "channel/gain");
  mapping.bindMixerRoot(mixer, root);
  mapping.connect(mode == 0 ? nullptr : &mixer);
  auto *original = alias->getOriginal();
  std::cout << (original ? original->getTag() : 0) << ' ' << alias->isEnabled()
            << ' ' << found->isEnabled() << ' ' << fallback.isEnabled() << '\n';
}
