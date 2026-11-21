#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstring>
#include <iostream>
#include <string>

using namespace Core::Portable;
using Presonus::Mixer::MixerComponentBase;

namespace {
class ObservedValue : public NumericParam {
public:
  ObservedValue(const ParamInfo &info, float value)
      : NumericParam(info), value(value) {}
  ParamValue getValue() const override {
    std::cout << "value:" << getTag() << '\n';
    return value;
  }

private:
  float value;
};
class Settings : public Component {
public:
  void add(ObservedValue *parameter) { paramList.add(parameter); }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  ParamInfo info[4]{};
  constexpr int tags[] = {20, 43, 5, 44};
  Settings settings;
  for (int i = 0; i < 4; ++i) {
    if (std::string(argv[2 + i]) == "none")
      continue;
    info[i].tag = tags[i];
    settings.add(new ObservedValue(info[i], std::stof(argv[2 + i])));
  }
  MixerComponentBase mixer;
  mixer.sceneSettings = &settings;
  const auto setup = mixer.getSetupProperty();
  std::uint32_t rate;
  std::memcpy(&rate, &setup.sampleRate, sizeof(rate));
  std::cout << "words:" << setup.type << ',' << setup.size << ',' << rate << ','
            << setup.word0c << ',' << setup.word10 << ',' << setup.word14 << ','
            << setup.word18 << ',' << static_cast<std::uint32_t>(setup.tag43)
            << ',' << static_cast<std::uint32_t>(setup.tag5) << ','
            << static_cast<std::uint32_t>(setup.tag44) << '\n';
  return 0;
}
