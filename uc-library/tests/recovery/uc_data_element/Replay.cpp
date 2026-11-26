#include "presonus/uc/DataElement.hpp"
#include "presonus/uc/meta_element.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
static const void *watchedBuffer, *watchedObject;
static unsigned bufferFrees, objectDeletes;
extern "C" void __real_free(void *);
extern "C" void __wrap_free(void *p) {
  if (p && p == watchedBuffer)
    ++bufferFrees;
  __real_free(p);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p && p == watchedObject)
    ++objectDeletes;
  __real__ZdlPv(p);
}
using namespace Presonus::UC;
using presonus::uc::DataElementAccess;
class Attributes final : public ElementAttributes {
public:
  const char *value = nullptr;
  mutable std::vector<std::string> calls;
  const char *lookupName(const char *key) const override {
    calls.push_back(std::string("lookup:") + key);
    return std::strcmp(key, "type") == 0 ? value : "fixture-id";
  }
  void storeName(const char *key, const char *value) override {
    calls.push_back(std::string("store:") + key + ":" + value);
  }
};
int main() {
  MetaElement metadata("DataElement", nullptr);
  auto *element = new DataElement(metadata);
  assert(element->isEmpty());
  auto &stream = DataElementAccess::stream(*element);
  assert(stream.getMemoryGrow() == 8192 && stream.getBytesWritten() == 0 &&
         stream.getPosition() == 0);
  assert(std::strcmp(DataElementAccess::type(*element), "") == 0);
  std::string a(31, 'A'), b(32, 'B'), c(80, 'C');
  const char embedded[] = "x\0tail";
  for (const char *value : {static_cast<const char *>(nullptr), "", "short",
                            a.c_str(), b.c_str(), c.c_str(), embedded}) {
    Attributes attrs;
    attrs.value = value;
    assert(element->load(attrs));
    assert(attrs.calls ==
           std::vector<std::string>({"lookup:type", "lookup:id"}));
    attrs.calls.clear();
    assert(element->save(attrs));
    const std::string type = DataElementAccess::type(*element);
    assert(attrs.calls == std::vector<std::string>(
                              {"store:type:" + type, "store:id:fixture-id"}));
    std::cout << type << '\n';
  }
  Core::Portable::Attributes storage(
      Core::Portable::AttributeAllocator::getDefault());
  LocalElementAttributes local(storage);
  storage.set("type", "provider");
  storage.set("id", "upstream-id");
  assert(element->load(local));
  assert(element->save(local));
  assert(std::strcmp(storage.getString("type"), "provider") == 0);
  assert(stream.writeBytes("payload", 7) == 7);
  assert(stream.getBytesWritten() == 7);
  stream.setPosition(0, Core::IO::kSeekSet);
  char out[8] = {};
  assert(stream.readBytes(out, 7) == 7 && std::strcmp(out, "payload") == 0);
  watchedBuffer = stream.getBuffer().getAddress();
  watchedObject = element;
  Element *base = element;
  delete base;
  assert(bufferFrees == 1 && objectDeletes == 1);
  std::cout << "provider-stream-virtual-delete-ok\n";
}
