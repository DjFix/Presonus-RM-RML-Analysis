#include "presonus/uc/element.hpp"
#include "presonus/uc/meta_element.hpp"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <string>
#include <string_view>
#include <type_traits>

using Presonus::UC::Element;
using presonus::uc::ElementAccess;
using Presonus::UC::MetaElement;

namespace {
std::array<void *, 8> nodes{};
std::array<int, 8> releases{};
std::size_t releaseCount = 0;
void *roster = nullptr;
bool observeRoster = false;
bool releasedRoster = false;
bool failRoster = false;
const Element *expectedParent = nullptr;
const Element *adopting = nullptr;

void require(bool condition) {
  if (!condition)
    std::abort();
}

void observeNodeFree(void *pointer) {
  for (std::size_t index = 0; index < nodes.size(); ++index) {
    if (pointer && pointer == nodes[index]) {
      require(releaseCount < releases.size());
      releases[releaseCount++] = static_cast<int>(index);
      return;
    }
  }
}

Element *makeElement(const MetaElement &metadata) {
  return new Element(metadata);
}

const MetaElement metadata("primary", makeElement);
const MetaElement alternative("alternate", makeElement);

struct DerivedElement : Element {
  explicit DerivedElement(const MetaElement &meta) : Element(meta) {}
};

template <class T> void inspectConstruction(const MetaElement &meta) {
  const T node(meta);
  require(ElementAccess::parent(node) == nullptr);
  require(node.isEmpty() && ElementAccess::childCapacity(node) == 0);
  require(ElementAccess::name(node)[0] == '\0');
  require(&node.getMetaElement() == &meta);
}

template <class T> void populate(T &parent, int count) {
  for (int n = 0; n < count; ++n) {
    auto child = std::make_unique<Element>(metadata);
    nodes[n + 1] = child.get();
    observeRoster = true;
    parent.addChild(child.get());
    observeRoster = false;
    require(ElementAccess::parent(*child) == &parent);
    require(parent.getIndex(child.get()) == n);
    child.release();
  }
}

void reportDestruction(int count, bool retained) {
  require(releaseCount == static_cast<std::size_t>(count + !retained));
  for (int n = 0; n < count; ++n)
    require(releases[n] == n + 1);
  if (!retained)
    require(releases[count] == 0);
  require(count == 0 || releasedRoster);
  require(metadata.isClass("primary"));
  std::cout << retained << ' ' << (count == 0 || releasedRoster);
  for (std::size_t n = 0; n < releaseCount; ++n)
    std::cout << ' ' << releases[n];
  std::cout << '\n';
}
} // namespace

extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
extern "C" void __real__ZdaPv(void *) noexcept;

extern "C" void *__wrap__Znam(std::size_t size) {
  if (adopting)
    require(ElementAccess::parent(*adopting) == expectedParent);
  if (failRoster)
    throw std::bad_alloc();
  void *pointer = __real__Znam(size);
  if (observeRoster) {
    roster = pointer;
    releasedRoster = false;
  }
  return pointer;
}

extern "C" void __wrap__ZdaPv(void *pointer) noexcept {
  if (pointer && pointer == roster)
    releasedRoster = true;
  __real__ZdaPv(pointer);
}

extern "C" void __wrap__ZdlPv(void *pointer) noexcept {
  observeNodeFree(pointer);
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) noexcept {
  observeNodeFree(pointer);
  __real__ZdlPvm(pointer, size);
}

int main(int argc, char **argv) {
  if (argc < 2)
    return 1;
  const std::string_view task = argv[1];
  if (task == "provider-name") {
    const Core::CString64 name;
    std::cout << name.length() << '\n';
    return 0;
  }
  if (argc < 3)
    return 1;
  const int first = std::stoi(argv[2]);
  if (task == "provider-capacity" && argc == 4) {
    Core::Vector<std::uint32_t> vector(0, 5);
    for (int n = 0; n < first; ++n)
      require(vector.add(n));
    require(vector.resize(std::stoi(argv[3])));
    std::cout << vector.getCapacity() << '\n';
    return 0;
  }
  const MetaElement &meta = first == 0 ? metadata : alternative;
  if (task == "complete_construct" || task == "base_construct") {
    if (task == "base_construct")
      inspectConstruction<DerivedElement>(meta);
    else
      inspectConstruction<Element>(meta);
    std::cout << "0 0 0 empty " << first << '\n';
  } else if (task == "complete_destroy" || task == "base_destroy") {
    if (task == "complete_destroy") {
      Element node(metadata);
      nodes[0] = &node;
      populate(node, first);
    } else {
      DerivedElement node(metadata);
      nodes[0] = &node;
      populate(node, first);
    }
    reportDestruction(first, true);
  } else if (task == "deleting_destroy") {
    Element *node = new Element(metadata);
    nodes[0] = node;
    populate(*node, first);
    delete node;
    reportDestruction(first, false);
  } else if (task == "get_meta_element") {
    Element node(meta);
    require(&node.getMetaElement() == &meta);
    std::cout << first << '\n';
  } else {
    Element node(metadata);
    populate(node, first);
    if (task == "is_empty") {
      ElementAccess::setName(node, "parent");
      std::cout << node.isEmpty() << '\n';
      require(std::string_view(ElementAccess::name(node)) == "parent");
    } else if (task == "get_index" && argc == 4) {
      const Element other(metadata);
      const int key = std::stoi(argv[3]);
      const auto *query = key < 0 ? nullptr
                          : key < first
                              ? static_cast<const Element *>(nodes[key + 1])
                              : &other;
      std::cout << node.getIndex(query) << '\n';
    } else if (task == "find_child" && argc == 4) {
      const std::string longName(63, 'x');
      const char *labels[] = {"", "alpha", "alpha", longName.c_str()};
      require(first <= 4);
      for (int n = 0; n < first; ++n)
        ElementAccess::setName(*static_cast<Element *>(nodes[n + 1]),
                               labels[n]);
      const char *query =
          std::string_view(argv[3]) == "<null>" ? nullptr : argv[3];
      const auto *found = node.findChild(query);
      for (int n = 0; n < first; ++n)
        require(node.getIndex(static_cast<Element *>(nodes[n + 1])) == n);
      std::cout << (found ? node.getIndex(found) + 1 : 0) << '\n';
    } else if (task == "add_child" && argc == 4) {
      failRoster = std::stoi(argv[3]);
      const bool failure = failRoster;
      auto child = std::make_unique<Element>(metadata);
      adopting = child.get();
      expectedParent = &node;
      try {
        node.addChild(child.get());
        require(!failure);
      } catch (const std::bad_alloc &) {
        require(failure);
      }
      failRoster = false;
      adopting = nullptr;
      const bool linked = ElementAccess::parent(*child) == &node;
      require(linked != failure &&
              node.getIndex(child.get()) == (failure ? -1 : first));
      if (linked) {
        try {
          node.addChild(child.get());
          std::abort();
        } catch (const std::invalid_argument &) {
        }
      }
      std::cout << first + linked << ' ' << ElementAccess::childCapacity(node)
                << ' ' << linked;
      for (int n = 0; n < first; ++n) {
        const int index = node.getIndex(static_cast<Element *>(nodes[n + 1]));
        std::cout << ' ' << index + 1;
      }
      if (linked) {
        std::cout << ' ' << node.getIndex(child.get()) + 1;
        child.release();
      }
      std::cout << '\n';
    } else
      return 1;
  }
}
