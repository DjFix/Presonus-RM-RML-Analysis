#include "presonus/surface/AssignmentHandlerTable.hpp"

#include <cstdio>
#include <cstdlib>

namespace {
class Handler final : public Presonus::AssignmentHandler {
  const char *getName() const override { return ""; }
  void updateConnections() override {}
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return EXIT_FAILURE;
  Handler handler;
  Core::Vector<Presonus::AssignmentHandler *> entries;
  Presonus::AssignmentHandlerTable borrowed(entries);
  Presonus::AssignmentHandlerTable owned;
  const int mode = std::atoi(argv[2]);
  for (const char *entry = argv[1]; *entry; ++entry) {
    auto *item = *entry == '-' ? nullptr : &handler;
    if (mode == 0)
      owned.addHandler(item);
    else
      entries.add(item);
  }
  Presonus::AssignmentHandlerTable copied(mode == 0 ? owned : borrowed);
  if (mode == 2 && entries.count() != 0)
    entries.removeAt(entries.count() - 1);
  std::printf("%d\n", copied.countHandlers());
}
