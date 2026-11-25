#include "presonus/uc/element.hpp"
#include "presonus/uc/meta_element.hpp"

#include <cassert>
#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>

using Core::Portable::DefaultAllocatedAttributes;
using Presonus::UC::Element;
using presonus::uc::ElementAccess;
using Presonus::UC::LocalElementAttributes;
using Presonus::UC::MetaElement;

namespace {
struct RootNode : Element {
  using Element::Element;
  Element *getRoot() const override { return const_cast<RootNode *>(this); }
};

const char *nullable(const char *arg) {
  return std::string_view(arg) == "<null>" ? nullptr : arg;
}
} // namespace

int main(int argc, char **argv) {
  assert(argc >= 2);
  const std::string task = argv[1];
  const MetaElement metadata("match", nullptr);
  if (task == "provider-string") {
    Core::CString64 value("previous");
    value = nullable(argv[2]);
    std::cout << value.length() << ' ' << value.str();
  } else if (task == "provider-capacity") {
    Core::Vector<Element *> roster;
    assert(roster.resize(std::atoi(argv[2])));
    assert(roster.resize(std::atoi(argv[3])));
    std::cout << roster.getCapacity();
  } else if (task == "provider-lookup") {
    DefaultAllocatedAttributes data;
    if (const char *value = nullable(argv[3]))
      data.set("id", value);
    LocalElementAttributes adapter(data);
    const char *value = adapter.lookupName(argv[2]);
    std::cout << (value ? std::string("@") + value : "<null>");
  } else if (task == "get_root") {
    const int depth = std::atoi(argv[2]);
    Element *tree = depth == 3 ? new RootNode(metadata) : new Element(metadata);
    const Element *receiver = tree;
    Element *parent = tree;
    for (int i = 0; i < (depth == 3 ? 2 : depth); ++i) {
      auto *child = new Element(metadata);
      parent->addChild(child);
      parent = child;
      receiver = child;
    }
    const auto *root = receiver->getRoot();
    assert(!root || root == tree);
    std::cout << (root != nullptr);
    delete tree;
  } else if (task == "is_element_class") {
    const Element element(metadata);
    std::cout << element.isElementClass(nullable(argv[2]));
  } else {
    DefaultAllocatedAttributes data;
    data.set("keep", 902);
    LocalElementAttributes adapter(data);
    Element element(metadata);
    if (task == "load_local_attributes") {
      if (const char *input = nullable(argv[2]))
        data.set("id", input);
      ElementAccess::setName(element, "previous");
      const bool ok = element.load(adapter);
      const char *name = ElementAccess::name(element);
      assert(std::string(name).size() <= 63);
      std::cout << ok << " @" << name;
    } else {
      assert(task == "save_local_attributes");
      data.set("id", "previous");
      ElementAccess::setName(element, argv[2]);
      const bool ok = element.save(adapter);
      assert(std::string(ElementAccess::name(element)) == argv[2]);
      std::cout << ok << " @" << data.getString("id");
    }
    assert(data.getInt("keep") == 902);
  }
}
