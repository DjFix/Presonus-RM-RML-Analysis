#include "presonus/SLChannel.hpp"

#include <array>
#include <iostream>
#include <string_view>

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  using namespace Core::Portable;
  using Vector = Core::Vector<Parameter *>;
  const std::string_view route(argv[1]), shape(argv[2]);
  const ParamInfo info{};
  NumericParam first(info), second(info);
  Vector parameters;
  if (shape == "single") {
    parameters.add(&first);
  } else if (shape == "mixed") {
    for (auto *value :
         std::array<Parameter *, 4>{&second, nullptr, &first, &second})
      parameters.add(value);
  } else if (shape != "empty") {
    return 2;
  }
  const auto before = parameters;
  auto *const backing = parameters.getItems();
  const auto capacity = parameters.getCapacity();
  const auto delta = parameters.getDelta();
  const auto firstValue = first.getValue();
  const auto secondValue = second.getValue();
  const Presonus::SLChannelBase channel("offline channel");
  const auto receiverType = channel.getClassID();
  if (route == "direct") {
    channel.Presonus::SLChannelBase::getSlowLinkParams(parameters);
  } else if (route == "vtable") {
    (channel.*(&Presonus::SLChannelBase::getSlowLinkParams))(parameters);
  } else {
    return 2;
  }
  bool same = parameters.count() == before.count() &&
              parameters.getItems() == backing &&
              parameters.getCapacity() == capacity &&
              parameters.getDelta() == delta;
  for (int i = 0; same && i < before.count(); ++i)
    same = parameters.at(i) == before.at(i);
  std::cout << (same && channel.getClassID() == receiverType &&
                first.getValue() == firstValue &&
                second.getValue() == secondValue)
            << '\n';
}
