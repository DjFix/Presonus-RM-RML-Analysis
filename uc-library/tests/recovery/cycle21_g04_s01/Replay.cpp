#include "presonus/LinkableComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace Core::Portable;
namespace {
struct Boundary final : Presonus::linkable_port::Boundary {
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    std::abort();
  }
  void remove(Presonus::LinkableComponent &) override { std::abort(); }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    std::abort();
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    std::abort();
  }
};
struct Child final : Component {
  Child(const Attributes &parentInput, const Attributes &previous, bool value)
      : Component("child"), parentInput(parentInput), previous(previous),
        value(value) {}
  bool load(const InputStorage &storage) override {
    const bool ordered = previous.lookup("old") != nullptr;
    const bool correctInput =
        &storage.getAttributes() == parentInput.getAttributes("child");
    std::cout << ordered << ' ' << correctInput << ' ';
    return value;
  }
  const Attributes &parentInput;
  const Attributes &previous;
  bool value;
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const bool childResult = std::string_view(argv[1]) == "1";
  const bool incoming = std::string_view(argv[2]) == "1";
  const bool ignore = std::string_view(argv[3]) == "1";
  Boundary boundary;
  Presonus::linkable_port::State state;
  Presonus::LinkableComponent component(state, boundary);
  Attributes attributes(AttributeAllocator::getDefault());
  attributes.makeAttributes("child")->set("payload", 4);
  if (incoming)
    attributes.makeAttributes("altmem")->set("new", 27);
  state.alternate.set("old", 12);
  state.component.addChild(new Child(attributes, state.alternate, childResult));
  InputStorage storage(attributes);
  storage.setMode(ignore ? "ignoreAltMemory" : "preset");
  const bool result = component.load(storage);
  std::cout << result << ' ' << (state.alternate.lookup("old") != nullptr)
            << ' ' << (state.alternate.lookup("new") != nullptr) << '\n';
}
