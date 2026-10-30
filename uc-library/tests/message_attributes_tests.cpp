#include "presonus/uc/message_attributes.hpp"
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

namespace message_test {
using Core::Portable::Attribute;
using Core::Portable::AttributeAllocator;
using Core::Portable::Attributes;
using Core::Portable::AttributeValue;
using Presonus::UC::MessageAttributes;
bool capture = false, expectObjectAllocation = false;
void *objectMemory = nullptr;
const char *expectedInput = nullptr, *lastGetResult = nullptr;
AttributeValue *lastAttribute = nullptr;
std::string lastKey;
std::vector<std::string> events;
unsigned objectAllocations = 0, actualObjectFrees = 0;
void require(bool value, const char *message) {
  if (!value)
    throw std::runtime_error(message);
}
void event(const std::string &value) {
  if (capture)
    events.push_back(value);
}
std::string trace() {
  std::string result;
  for (const auto &e : events) {
    if (!result.empty())
      result += ',';
    result += e;
  }
  return result.empty() ? "-" : result;
}
void recordFree(void *p) {
  if (p == objectMemory && p) {
    ++actualObjectFrees;
    event("delete");
    objectMemory = nullptr;
  }
}
std::string unhex(const std::string &text) {
  if (text == "-" || text == "_")
    return {};
  require(text.size() % 2 == 0, "invalid hex fixture");
  std::string result;
  for (unsigned i = 0; i < text.size(); i += 2)
    result.push_back(
        static_cast<char>(std::stoul(text.substr(i, 2), nullptr, 16)));
  return result;
}
} // namespace message_test
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  auto *p = __real__Znwm(size);
  if (message_test::expectObjectAllocation) {
    message_test::expectObjectAllocation = false;
    message_test::objectMemory = p;
    ++message_test::objectAllocations;
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) {
  message_test::recordFree(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  message_test::recordFree(p);
  __real__ZdlPvm(p, size);
}
extern "C" message_test::AttributeAllocator &
__real__ZN4Core8Portable18AttributeAllocator10getDefaultEv();
extern "C" message_test::AttributeAllocator &
__wrap__ZN4Core8Portable18AttributeAllocator10getDefaultEv() {
  auto &result = __real__ZN4Core8Portable18AttributeAllocator10getDefaultEv();
  message_test::event("allocator");
  return result;
}
extern "C" void
__real__ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE(
    message_test::Attributes *, message_test::AttributeAllocator &);
extern "C" void
__wrap__ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE(
    message_test::Attributes *self,
    message_test::AttributeAllocator &allocator) {
  using namespace message_test;
  if (capture)
    require(self == objectMemory, "base constructor this mismatch");
  event("base_ctor");
  __real__ZN4Core8Portable10AttributesC2ERNS0_18AttributeAllocatorE(self,
                                                                    allocator);
}
extern "C" void
__real__ZN4Core8Portable10AttributesD2Ev(message_test::Attributes *);
extern "C" void
__wrap__ZN4Core8Portable10AttributesD2Ev(message_test::Attributes *self) {
  using namespace message_test;
  if (capture)
    require(self == objectMemory, "base destructor this mismatch");
  event("base_dtor");
  __real__ZN4Core8Portable10AttributesD2Ev(self);
}
extern "C" const char *__real__ZNK4Core8Portable10Attributes9getStringEPKc(
    const message_test::Attributes *, const char *);
extern "C" const char *__wrap__ZNK4Core8Portable10Attributes9getStringEPKc(
    const message_test::Attributes *self, const char *key) {
  using namespace message_test;
  const auto *result =
      __real__ZNK4Core8Portable10Attributes9getStringEPKc(self, key);
  if (capture) {
    require(self == objectMemory, "getString this mismatch");
    event(std::string("get:") + key);
    lastGetResult = result;
  }
  return result;
}
extern "C" message_test::Attribute &
__real__ZN4Core8Portable10Attributes11lookupOrAddEPKc(
    message_test::Attributes *, const char *);
extern "C" message_test::Attribute &
__wrap__ZN4Core8Portable10Attributes11lookupOrAddEPKc(
    message_test::Attributes *self, const char *key) {
  using namespace message_test;
  auto &result =
      __real__ZN4Core8Portable10Attributes11lookupOrAddEPKc(self, key);
  if (capture) {
    require(self == objectMemory, "lookup this mismatch");
    event(std::string("lookup:") + key);
    lastAttribute = &result;
    lastKey = key;
  }
  return result;
}
extern "C" void __real__ZN4Core8Portable14AttributeValue3setEPKcb(
    message_test::AttributeValue *, const char *, bool);
extern "C" void __wrap__ZN4Core8Portable14AttributeValue3setEPKcb(
    message_test::AttributeValue *self, const char *value, bool shared) {
  using namespace message_test;
  if (capture) {
    require(self == lastAttribute && value == expectedInput && !shared,
            "setter receiver/input identity/shared flag mismatch");
    event("set:" + lastKey + ":0");
  }
  __real__ZN4Core8Portable14AttributeValue3setEPKcb(self, value, shared);
}
int main(int argc, char **argv) {
  using namespace message_test;
  try {
    require(argc == 2, "fixture required");
    std::ifstream input(argv[1]);
    require(bool(input), "missing fixture");
    std::string role, action, encoded, expected;
    unsigned cases = 0, sourceCases = 0;
    while (input >> role >> action >> encoded >> expected) {
      auto value = unhex(encoded);
      expectedInput = encoded == "-" ? nullptr : value.c_str();
      expectObjectAllocation = true;
      void *storage = ::operator new(sizeof(MessageAttributes));
      MessageAttributes *object = nullptr;
      capture = false;
      if (action[0] != 'C')
        object = new (storage) MessageAttributes(nullptr);
      const std::string key = action.size() > 2 ? action.substr(1) : "id";
      if (action[0] == 'G' && expectedInput)
        object->Attributes::set(key.c_str(), expectedInput, true);
      if (action[0] == 'S') {
        object->Attributes::set(key.c_str(), "previous owned value", false);
        object->Attributes::set("other", "keep", false);
      }
      if (action[0] == 'D') {
        object->setSource("owned source data");
        object->setURL("owned url data");
      }
      events.clear();
      capture = true;
      if (action[0] == 'C')
        object = new (storage) MessageAttributes(expectedInput);
      else if (action[0] == 'G') {
        const auto *result = key == "src"   ? object->getSource()
                             : key == "url" ? object->getURL()
                                            : object->getID();
        require(result == lastGetResult,
                "getter did not forward actual provider");
        require((result == nullptr) == (expectedInput == nullptr),
                "getter null state mismatch");
        if (result)
          require(std::strcmp(result, expectedInput) == 0,
                  "getter text mismatch");
      } else if (action[0] == 'S') {
        if (key == "src")
          object->setSource(expectedInput);
        else if (key == "url")
          object->setURL(expectedInput);
        else
          object->setID(expectedInput);
      } else if (action == "D1") {
        object->~MessageAttributes();
      } else if (action == "D0") {
        Attributes *base = object;
        delete base;
      } else {
        require(false, "unknown action");
      }
      capture = false;
      if (trace() != expected) {
        std::cerr << role << ' ' << action << " actual=" << trace()
                  << " expected=" << expected << '\n';
        require(false, "actual CCL app boundary order mismatch");
      }
      if (action[0] == 'C') {
        for (auto byte :
             presonus::uc::MessageAttributesPortAccess::opaqueState(*object))
          require(byte == 0, "opaque app state not zero");
        require(object->countAttributes() == (expectedInput ? 1 : 0),
                "actual CCL constructor optional ID count mismatch");
      }
      if (action[0] == 'S') {
        const char *stored = object->Attributes::getString(key.c_str());
        require(object->countAttributes() == 2 &&
                    std::strcmp(object->Attributes::getString("other"),
                                "keep") == 0,
                "setter corrupted unrelated real provider attribute");
        if (expectedInput && !value.empty())
          require(stored && std::strcmp(stored, expectedInput) == 0,
                  "actual provider copied value mismatch");
        else
          require(stored == nullptr,
                  "actual provider null/empty contract mismatch");
      }
      if (action == "D0")
        require(objectMemory == nullptr,
                "D0 did not forward actual deallocation");
      else if (action == "D1") {
        require(objectMemory == storage, "D1 unexpectedly deallocated");
        ::operator delete(storage);
      } else {
        delete object;
      }
      require(objectMemory == nullptr, "object allocation leaked");
      ++cases;
    }
    // Independent actual-source provider checks, not original Core behavior:
    // cross-key aliases remain valid; same-key self/substrings are excluded.
    for (unsigned i = 0; i < 32; ++i) {
      MessageAttributes object("id");
      object.setSource("shared cross key text");
      const auto *source = object.getSource();
      object.setURL(source);
      object.setSource("replacement");
      require(std::strcmp(object.getURL(), "shared cross key text") == 0 &&
                  std::strcmp(object.getID(), "id") == 0,
              "actual public API cross-key copy contract mismatch");
      ++sourceCases;
    }
    require(cases == 320 && objectAllocations == actualObjectFrees,
            "case count or actual deallocation imbalance");
    std::cout << "PASS original_app_cases=" << cases
              << " actual_source_cases=" << sourceCases
              << " actual_object_allocations=" << objectAllocations
              << " actual_forwarded_object_frees=" << actualObjectFrees
              << " actual_Core_boundaries=matched\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
