#include "core/system/coretime.h"
#include "presonus/uc/ClientRootComponent.hpp"

#include <cstdint>
#include <iostream>
#include <string>
#include <string_view>

namespace {
bool controlledClock = false;
std::int64_t ticks = 0;
int monotonicCalls = 0;
} // namespace

extern "C" int __real_clock_gettime(clockid_t clock, timespec *time);

extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *time) {
  if (!controlledClock || clock != CLOCK_MONOTONIC)
    return __real_clock_gettime(clock, time);
  ++monotonicCalls;
  time->tv_sec = ticks / 1000000000;
  time->tv_nsec = ticks % 1000000000;
  if (time->tv_nsec < 0) {
    --time->tv_sec;
    time->tv_nsec += 1000000000;
  }
  return 0;
}

int main(int argc, char **argv) {
  using Presonus::UC::ClientRootComponent;
  if (argc < 2)
    return 2;
  const std::string_view method(argv[1]);
  ClientRootComponent root("root"), other("distinct root");
  if (method == "cast_to" && argc == 3) {
    const int type = std::stoi(argv[2]);
    auto &component = static_cast<Core::Portable::Component &>(root);
    auto *value = component.castTo(type);
    const auto *typed =
        Core::Portable::core_cast<ClientRootComponent>(&component);
    const auto *base =
        Core::Portable::core_cast<Core::Portable::Component>(&component);
    if (typed != &root || base != &component || &root == &other)
      return 3;
    if (value != nullptr && value != &root)
      return 4;
    std::cout << (value != nullptr) << '\n';
  } else if (method == "get_root" && argc == 2) {
    auto *result = root.getRoot();
    std::cout << (result == &root && other.getRoot() == &other &&
                  result != &other &&
                  std::string_view(root.getName()) == "root")
              << '\n';
  } else if (method == "get_system_time" && argc == 3) {
    const ClientRootComponent &component = root;
    const auto before = Core::SystemClock::getTime() / 1000000;
    const auto current = component.getSystemTime();
    const auto after = Core::SystemClock::getTime() / 1000000;
    if (current < before || current > after)
      return 5;
    ticks = std::stoll(argv[2]);
    controlledClock = true;
    const auto value = component.getSystemTime();
    if (monotonicCalls != 1)
      return 6;
    std::cout << value << '\n';
  } else
    return 2;
}
