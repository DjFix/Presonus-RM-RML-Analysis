#include "presonus/surface/DawFxPageComponent.hpp"
#include <iostream>
#include <vector>

namespace {
struct Context {
  int id;
  std::vector<bool> updates;
};

presonus::surface::DawFxBindings bind(Context &context) {
  return {&context, [](void *) { return true; }, [](void *) { return 16; },
          [](void *pointer, bool force) {
            auto &context = *static_cast<Context *>(pointer);
            context.updates.push_back(force);
            std::cout << context.id << ' ' << force << '\n';
          }};
}
} // namespace

int main() {
  Context firstContext{0, {}}, secondContext{1, {}};
  Presonus::Surface::DawFxPageComponent first(nullptr, bind(firstContext), 5);
  Presonus::Surface::DawFxPageComponent second(nullptr, bind(secondContext));
  first.onFocusChannelChanged();
  second.onFocusChannelChanged();
  if (first.getListOffset() != 5 || second.getListOffset() != 0)
    return 1;
  first.setListOffset(10);
  first.setListOffset(10);
  return first.getListOffset() == 10 &&
                 firstContext.updates == std::vector<bool>{true, false} &&
                 secondContext.updates == std::vector<bool>{true}
             ? 0
             : 1;
}
