#include "presonus/surface_panel/ControlGroup.hpp"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>

namespace {
struct TestControl {
  int id = 0;
  int tag = 0;
};
int tagOf(void *, const Presonus::Panel::Control *control) {
  return reinterpret_cast<const TestControl *>(control)->tag;
}
Presonus::Panel::Control *handle(TestControl &control) {
  return reinterpret_cast<Presonus::Panel::Control *>(&control);
}
int identity(const Presonus::Panel::Control *control) {
  return control ? reinterpret_cast<const TestControl *>(control)->id : 0;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  std::ifstream input(argv[1]);
  if (!input)
    return 2;
  char operation;
  int size, argument, sentinel, errorTag, expected, afterCount;
  unsigned cases = 0;
  while (input >> operation >> size >> argument >> sentinel >> errorTag >>
         expected >> afterCount) {
    std::array<TestControl, 259> objects;
    for (int i = 0; i < 259; ++i)
      objects[i] = {i, errorTag};
    presonus::panel_binding::ControlGroupState state;
    state.tagOf = tagOf;
    for (int i = 1; i <= size; ++i) {
      if (!(input >> objects[i].tag))
        return 3;
      if (!state.controls.add(handle(objects[i])))
        return 4;
    }
    auto &error = Core::ConstVector<Presonus::Panel::Control *>::getError();
    error = sentinel ? handle(objects[sentinel]) : nullptr;
    Presonus::Panel::ControlGroup group(state);
    int actual = 0;
    if (operation == 'C')
      actual = group.count();
    else if (operation == 'A')
      actual = identity(group.at(argument));
    else if (operation == 'T')
      actual = identity(group.byTag(argument));
    else if (operation == 'D')
      group.add(argument ? handle(objects[argument]) : nullptr);
    else
      return 5;
    if (actual != expected || group.count() != afterCount) {
      std::cerr << "Mismatch case " << cases << " op=" << operation << '\n';
      return 6;
    }
    for (int i = 0; i < afterCount; ++i) {
      const int expectedIdentity = i < size ? i + 1 : argument;
      if (identity(group.at(i)) != expectedIdentity)
        return 7;
    }
    if (identity(error) != sentinel)
      return 8;
    ++cases;
  }
  Core::ConstVector<Presonus::Panel::Control *>::getError() = nullptr;
  if (!input.eof() || cases == 0)
    return 9;
  std::cout << "PASS " << cases << " original ARM ControlGroup cases; real CCL "
            << "FixedSizeVector storage\n";
}
