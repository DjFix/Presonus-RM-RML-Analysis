#include "presonus/SLChannel.hpp"
#include <array>
#include <iostream>

int main() {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  Core::Portable::NumericParam selection(info), colorIndex(info), first(info),
      second(info), other(info);
  std::array<Core::Portable::Parameter *, 3> values{nullptr, &first, &second};
  Presonus::SLChannel firstChannel("first", &selection);
  Presonus::SLChannel secondChannel("second", &selection);
  Presonus::SLChannelBase base("base");
  firstChannel.bindColorIndexParameter(&colorIndex);
  secondChannel.bindColorIndexParameter(&colorIndex);
  firstChannel.bindLinkedSelectionParameter(&other);
  secondChannel.bindLinkedSelectionParameter(&other);
  if (firstChannel.getColorParameter() || secondChannel.getColorParameter() ||
      base.getColorParameter())
    return 2;

  const auto initialIndex = firstChannel.getColorIndex();
  int identity, instance;
  while (std::cin >> identity >> instance) {
    if (identity < 0 || identity > 2 || instance < 0 || instance > 1)
      return 2;
    auto &channel = instance == 0 ? firstChannel : secondChannel;
    channel.bindColorParameter(values[identity]);
    const Presonus::SLChannelBase &view = channel;
    if (view.getSelectionParameter() != &selection ||
        view.getLinkedSelectionParameter() != &other ||
        view.getColorIndex() != initialIndex ||
        channel.Presonus::SLChannelBase::getColorParameter() != nullptr)
      return 3;
    const auto *result = view.getColorParameter();
    int index = -1;
    for (int value = 0; value < 3; ++value)
      if (result == values[value])
        index = value;
    std::cout << index << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
