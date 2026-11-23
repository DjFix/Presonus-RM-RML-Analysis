#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <iostream>

using Presonus::AssignmentHandler;
using Presonus::AssignmentHandlerTable;

extern "C" void constructC1(AssignmentHandlerTable *) asm(
    "_ZN8Presonus22AssignmentHandlerTableC1Ev");
extern "C" void constructC2(AssignmentHandlerTable *) asm(
    "_ZN8Presonus22AssignmentHandlerTableC2Ev");

namespace {
void require(bool test) {
  if (!test)
    std::abort();
}

class Handler final : public AssignmentHandler {
public:
  explicit Handler(const char *name) : name_(name) {}
  void *castTo(int) override { return nullptr; }
  const char *getName() const override { return name_; }
  void updateConnections() override { std::abort(); }
  void onModifiersChanged() override { std::abort(); }
  void onIdle() override { std::abort(); }
  void setController(Presonus::IMappingController *) override { std::abort(); }
  void initialize(Core::Portable::Component *component) override {
    require(component == nullptr);
    ++initializations;
  }
  int initializations = 0;

private:
  const char *name_;
};

void checkOwned(void (*construct)(AssignmentHandlerTable *), const char *name) {
  alignas(AssignmentHandlerTable) unsigned char
      storage[sizeof(AssignmentHandlerTable)];
  auto *table = reinterpret_cast<AssignmentHandlerTable *>(storage);
  construct(table);
  AssignmentHandlerTable independent;
  Handler first("first");
  Handler second("second");
  require(table->findHandler("first") == nullptr);
  table->initializeHandlers(nullptr);
  require(first.initializations == 0);
  table->addHandler(&first);
  table->addHandler(&second);
  require(table->getHandler(0) == &first && table->getHandler(1) == &second);
  require(table->findHandler("second") == &second);
  require(independent.findHandler("first") == nullptr);
  table->initializeHandlers(nullptr);
  require(first.initializations == 1 && second.initializations == 1);
  AssignmentHandlerTable copy(*table);
  table->removeHandler(&first);
  require(table->findHandler("first") == nullptr &&
          copy.findHandler("first") == &first);
  require(table->getHandler(0) == &second);
  table->~AssignmentHandlerTable();
  require(copy.findHandler("second") == &second);
  std::cout << name << " empty owned isolated non-owning\n";
}

void checkBorrowed() {
  Core::Vector<AssignmentHandler *> storage;
  Handler first("first");
  Handler second("second");
  storage.add(&first);
  {
    AssignmentHandlerTable table(storage);
    AssignmentHandlerTable copy(table);
    require(copy.findHandler("first") == &first);
    table.addHandler(&second);
    require(storage.count() == 2 && copy.getHandler(1) == &second);
    copy.removeHandler(&first);
    require(storage.count() == 1 && table.findHandler("first") == nullptr);
  }
  require(storage.count() == 1 && storage.at(0) == &second);
  std::cout << "borrowed shared non-owning\n";
}
} // namespace

int main() {
  checkOwned(constructC1, "C1");
  checkOwned(constructC2, "C2");
  checkBorrowed();
}
