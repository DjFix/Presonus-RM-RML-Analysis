#include "presonus/SLChannel.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using namespace Core::Portable;
using Presonus::SLChannelBase;

class Channel final : public SLChannelBase {
public:
  using SLChannelBase::SLChannelBase;
  ColorParam *color = nullptr;
  Parameter *getColorParameter() const override { return color; }
  void bindUnlistedParent(Component *owner) { parent = owner; }
};

int number(int position, int count) {
  Component parent("parent");
  Channel channel("tested");
  std::vector<Component *> owned;
  if (position < 0)
    return channel.getNumber();
  for (int i = 0; i < count; ++i) {
    auto *child = i == position ? static_cast<Component *>(&channel)
                                : new Component("sibling");
    parent.addChild(child);
    if (child != &channel)
      owned.push_back(child);
  }
  if (position >= count)
    channel.bindUnlistedParent(&parent);
  const auto observed = channel.getNumber();
  if (position >= count)
    channel.bindUnlistedParent(nullptr);
  else
    parent.removeChild(&channel);
  // parent owns sibling cleanup.
  return observed;
}
} // namespace

int main(int argc, char **argv) {
  constexpr int task = 16;
  if constexpr (task == 16) {
    if (argc != 3)
      return 2;
    std::cout << number(std::atoi(argv[1]), std::atoi(argv[2])) << '\n';
  } else {
    if (argc > 2)
      return 2;
    Channel channel("tested");
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    NumericParam numeric(info);
    ColorParam color(info);
    const SLChannelBase &base = channel;
    if constexpr (task == 13) {
      if (argc == 2) {
        numeric.setMin(-256.f);
        numeric.setMax(256.f);
        numeric.setValue(std::strtof(argv[1], nullptr));
        channel.bindColorIndexParameter(&numeric);
      }
      std::cout << base.getColorIndex() << '\n';
    } else {
      if (argc == 2) {
        color.setColor(static_cast<ColorParam::ColorValue>(
                           std::strtoul(argv[1], nullptr, 10)),
                       false);
        channel.color = &color;
      }
      std::cout << static_cast<Core::uint32>(base.getColor()) << '\n';
    }
  }
}
