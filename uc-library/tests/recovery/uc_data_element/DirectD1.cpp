#include "presonus/uc/DataElement.hpp"
#include "presonus/uc/meta_element.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <new>

static const void *parentStorage, *bufferStorage;
static unsigned bufferFrees, parentFrees, parentDeletes, baseDestructions;
extern "C" void __real_free(void *);
extern "C" void __wrap_free(void *p) {
  if (p && p == bufferStorage)
    ++bufferFrees;
  if (p && p == parentStorage)
    ++parentFrees;
  __real_free(p);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p && p == parentStorage)
    ++parentDeletes;
  __real__ZdlPv(p);
}
extern "C" void __real__ZN8Presonus2UC7ElementD2Ev(void *);
extern "C" void __wrap__ZN8Presonus2UC7ElementD2Ev(void *p) {
  if (p == parentStorage)
    ++baseDestructions;
  __real__ZN8Presonus2UC7ElementD2Ev(p);
}
int main() {
  using namespace Presonus::UC;
  MetaElement metadata("DataElement", nullptr);
  void *storage = ::operator new(sizeof(DataElement));
  auto *element = new (storage) DataElement(metadata);
  auto &stream = presonus::uc::DataElementAccess::stream(*element);
  assert(stream.writeBytes("direct-d1-payload", 17) == 17);
  assert(stream.getBytesWritten() == 17);
  stream.setPosition(0, Core::IO::kSeekSet);
  char copied[18] = {};
  assert(stream.readBytes(copied, 17) == 17);
  assert(std::strcmp(copied, "direct-d1-payload") == 0);
  parentStorage = storage;
  bufferStorage = stream.getBuffer().getAddress();
  assert(bufferStorage && bufferStorage != parentStorage);

  element->DataElement::~DataElement();

  std::cout << "after_complete_d1 buffer_frees=" << bufferFrees
            << " base_d2_calls=" << baseDestructions
            << " parent_deletes=" << parentDeletes
            << " parent_frees=" << parentFrees << '\n';
  assert(bufferFrees == 1 && baseDestructions == 1);
  assert(parentDeletes == 0 && parentFrees == 0);
  // Object lifetime has ended; the caller still owns its raw allocation.
  ::operator delete(storage);
  std::cout << "after_caller_storage_cleanup parent_deletes=" << parentDeletes
            << " buffer_frees=" << bufferFrees << '\n';
  assert(parentDeletes == 1 && bufferFrees == 1);
}
