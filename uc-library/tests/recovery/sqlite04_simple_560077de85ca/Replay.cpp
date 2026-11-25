#include "presonus/dsp/ControllerProperties.hpp"
#include "presonus/dsp/SimpleController.hpp"

#include <bit>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
#include <vector>

using Presonus::Dsp::ParamDescriptorList;
using Presonus::Dsp::SetupProperty;
using Presonus::Dsp::SimpleController;

namespace {
using Word = std::uint32_t;
const void *integerStorage = nullptr;
const void *floatStorage = nullptr;
const void *receiver = nullptr;
bool recording = false;
bool watchingAllocations = false;
std::vector<std::string> events;

void recordArrayFree(void *ptr) {
  if (recording && ptr == integerStorage)
    events.emplace_back("free_int");
  if (recording && ptr == floatStorage)
    events.emplace_back("free_float");
  if (ptr && ptr == integerStorage)
    integerStorage = nullptr;
  if (ptr && ptr == floatStorage)
    floatStorage = nullptr;
}
} // namespace

void *operator new[](std::size_t size) {
  if (auto *ptr = std::malloc(size ? size : 1)) {
    if (watchingAllocations) {
      if (floatStorage)
        integerStorage = ptr;
      else
        floatStorage = ptr;
    }
    return ptr;
  }
  throw std::bad_alloc{};
}

void operator delete[](void *ptr) noexcept {
  recordArrayFree(ptr);
  std::free(ptr);
}

void operator delete[](void *ptr, std::size_t) noexcept {
  ::operator delete[](ptr);
}

void operator delete(void *ptr) noexcept {
  if (recording && ptr == receiver)
    events.emplace_back("delete");
  std::free(ptr);
}

void operator delete(void *ptr, std::size_t) noexcept {
  ::operator delete(ptr);
}

namespace {

struct Target : Core::IPropertyHandler {
  std::vector<std::vector<Word>> messages;
  void setProperty(const Core::Property &property) override {
    std::vector<Word> words(property.size / 4);
    std::memcpy(words.data(), &property, property.size);
    messages.push_back(std::move(words));
  }
  void getProperty(Core::Property &) override {}
  void release() override { events.emplace_back("release"); }
};

class Filter : public SimpleController {
public:
  Filter(int id, const ParamDescriptorList *list, int skip)
      : SimpleController(id, list), skip_(skip) {}
  bool isInternal(int key) const override { return key == skip_; }

private:
  int skip_;
};

struct Incoming : Core::Property {
  Incoming(Word type, Word data, Word tag, Word value)
      : Property(type, sizeof(Incoming)), data(data), tag(tag), value(value) {}
  Word data, tag, value;
};

void printWords(const std::vector<Word> &words) {
  for (const auto word : words)
    std::cout << ' ' << word;
  std::cout << '\n';
}

} // namespace

int main() {
  int count, skip;
  bool lookup, filter, hasTarget, nullList, deleting, baseConstruction;
  if (!(std::cin >> count >> lookup >> filter >> skip >> hasTarget >>
        nullList >> deleting >> baseConstruction))
    return 2;
  ParamDescriptorList list(presonus::dsp::DescriptorSourceTag{});
  for (int index = 0; index < count; ++index) {
    const int tag = lookup ? index - 100 : index;
    const float initial = (index % 5) - 2.75f;
    if (index % 2)
      list.addToggle(tag, "", "", "", initial, "", 0);
    else
      list.addFloat(tag, "", "", "", -4.f, 4.f, initial, "", "", 0.5f, 0);
  }
  const auto *descriptors = nullList ? nullptr : &list;
  Target target;
  events.reserve(4);
  watchingAllocations = true;
  SimpleController *controller =
      (filter || baseConstruction) ? static_cast<SimpleController *>(new Filter(
                                         9, descriptors, filter ? skip : 0))
                                   : new SimpleController(9, descriptors);
  receiver = controller;
  controller->sourceState().lookupByTag = lookup;
  if (hasTarget)
    controller->setTarget(&target);

  std::string operation;
  while (std::cin >> operation) {
    int key;
    Word a, b, c, d;
    if (operation == "set") {
      std::cin >> key >> a;
      controller->setValue(key, std::bit_cast<float>(a));
    } else if (operation == "get") {
      std::cin >> key;
      target.messages.push_back(
          {std::bit_cast<Word>(controller->getValue(key))});
    } else if (operation == "internal") {
      std::cin >> key;
      target.messages.push_back({controller->isInternal(key)});
    } else if (operation == "setup") {
      std::cin >> a;
      SetupProperty setup;
      setup.rate = std::bit_cast<float>(a);
      controller->setupProcess(setup);
    } else if (operation == "property") {
      std::cin >> a >> b >> c >> d;
      if (a == 1399157877) {
        SetupProperty setup;
        setup.rate = std::bit_cast<float>(b);
        controller->setProperty(setup);
      } else {
        controller->setProperty(Incoming(a, b, c, d));
      }
    } else if (operation == "all") {
      controller->updateAll();
    } else if (operation == "updates" || operation == "drain") {
      controller->doUpdates();
    } else if (operation == "clear") {
      controller->sourceState().processDirty = 0;
    } else if (operation == "destroy") {
      recording = true;
      if (deleting)
        delete controller;
      else
        controller->SimpleController::~SimpleController();
      recording = false;
      if (!deleting)
        ::operator delete(controller);
      for (const auto &event : events)
        std::cout << "event " << event << '\n';
      controller = nullptr;
    } else {
      return 3;
    }
  }
  if (controller) {
    const auto &state = controller->sourceState();
    std::cout << "state";
    printWords({state.processDirty, state.byte1d, state.processRateBits,
                state.word04, static_cast<Word>(state.constructorId)});
    std::vector<Word> values;
    for (int index = 0; index < count && !nullList; ++index)
      values.push_back(std::bit_cast<Word>(
          controller->getValue(lookup ? index - 100 : index)));
    std::cout << "values";
    printWords(values);
    delete controller;
  }
  for (const auto &message : target.messages) {
    std::cout << "message";
    printWords(message);
  }
}
