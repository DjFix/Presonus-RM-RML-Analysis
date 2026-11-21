#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
using namespace Presonus;

struct RecordingHandler : AssignmentHandler {
  RecordingHandler(int index, Component &component)
      : index(index), expected(component) {}
  const char *getName() const override { return "record"; }
  void updateConnections() override {}
  void initialize(Component *component) override {
    if (component != &expected || component->countChildren() != 1 ||
        component->findChild("panel") == nullptr)
      std::abort();
    AssignmentHandler::initialize(component);
    std::cout << index << '\n';
  }
  int index;
  Component &expected;
};

int main(int argc, char **argv) {
  Component component("surface");
  component.addChild(new Component("panel"));
  RecordingHandler first(0, component), second(1, component);
  Core::Vector<AssignmentHandler *> storage;
  for (int arg = 1; arg < argc; ++arg)
    storage.add(argv[arg][0] == '0' ? &first : &second);
  AssignmentHandlerTable table(storage);
  table.initializeHandlers(&component);
  if (storage.count() != argc - 1 || component.countChildren() != 1)
    return 1;
}
