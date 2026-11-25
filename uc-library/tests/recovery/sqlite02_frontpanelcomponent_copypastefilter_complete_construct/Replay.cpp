#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"

#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <string_view>

using Core::Portable::core_cast;
using Core::Portable::IStorageFilter;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Mixer::ChannelComponent;
using Filter = Presonus::Panel::FrontPanelComponent::CopyPasteFilter;

namespace {
void require(bool condition) {
  if (!condition)
    std::abort();
}

struct DerivedFilter : Filter {
  explicit DerivedFilter(bool &destroyed) : destroyed(destroyed) {}
  ~DerivedFilter() { destroyed = true; }

  bool &destroyed;
};

template <class T> void lifecycle(bool tagged = false) {
  struct Storage {
    std::array<unsigned char, 16> prefix;
    alignas(T) std::array<unsigned char, sizeof(T)> object;
    std::array<unsigned char, 16> suffix;
  };
  auto storage = std::make_unique<Storage>();
  storage->prefix.fill(0xa5);
  storage->suffix.fill(0x5a);
  bool derivedDestroyed = false;
  T *object;
  if constexpr (std::is_same_v<T, DerivedFilter>)
    object = new (storage->object.data()) T(derivedDestroyed);
  else
    object = tagged ? new (storage->object.data())
                          T(Filter::SourcePortConstruction{})
                    : new (storage->object.data()) T;
  auto *interface = static_cast<IStorageFilter *>(object);
  require(dynamic_cast<Filter *>(interface) == static_cast<Filter *>(object));
  require(core_cast<IStorageFilter>(interface) == interface);
  require(interface->castTo(-1) == nullptr);
  require(interface->shouldSave(0, nullptr, nullptr));
  object->~T();
  if constexpr (std::is_same_v<T, DerivedFilter>)
    require(derivedDestroyed);
  for (auto byte : storage->prefix)
    require(byte == 0xa5);
  for (auto byte : storage->suffix)
    require(byte == 0x5a);
  std::cout << "dispatch-initialized receiver-retained\n";
}
} // namespace

int main(int argc, char **argv) {
  if (argc < 2)
    return 1;
  const std::string_view command = argv[1];
  if (command == "C1" || command == "D1")
    lifecycle<Filter>();
  else if (command == "C2" || command == "D2")
    lifecycle<DerivedFilter>();
  else if (command == "tagged")
    lifecycle<Filter>(true);
  else if (argc == 7 && (command == "describe" || command == "load")) {
    const int type = std::stoi(argv[2]);
    const bool hasObject = std::stoi(argv[3]);
    const bool hasName = std::stoi(argv[4]);
    const int controller = std::stoi(argv[5]);
    const int tag = std::stoi(argv[6]);
    ParamInfo info{};
    info.tag = tag;
    std::memcpy(info.name, "copy", sizeof("copy"));
    info.type = ParamInfo::kFloat;
    NumericParam parameter(info);
    Core::Portable::Component component;
    ChannelComponent channel(ChannelComponent::SourcePortConstruction{});
    if (controller == 1)
      parameter.setController(&component);
    else if (controller == 2)
      parameter.setController(&channel);

    if (command == "describe") {
      auto *actual = parameter.getController();
      std::cout << (actual != nullptr) << ' '
                << (core_cast<ChannelComponent>(actual) != nullptr) << ' '
                << parameter.getTag() << '\n';
    } else {
      Filter filter;
      const IStorageFilter &interface = filter;
      const char *name = hasName ? "copy" : nullptr;
      void *object = hasObject ? &parameter : nullptr;
      const bool load = interface.shouldLoad(type, name, object);
      require(parameter.getTag() == tag);
      require(parameter.getController() == (controller == 2   ? &channel
                                            : controller == 1 ? &component
                                                              : nullptr));
      require(load == interface.shouldSave(type, name, object));
      std::cout << load << '\n';
    }
  } else
    return 1;
}
