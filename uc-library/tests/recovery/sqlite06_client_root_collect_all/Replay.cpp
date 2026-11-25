#include "presonus/uc/ClientRootComponent.hpp"

#include "core/portable/coreattributes.h"

#include <cstring>
#include <iostream>
#include <string>
#include <string_view>

namespace {
using Core::Portable::Attributes;
using Core::Portable::AttributeValue;
using Core::Portable::ColorParam;
using Core::Portable::Component;
using Core::Portable::ParamInfo;
using Presonus::UC::ClientComponent;

void addParameter(Component &parent, const char *name, int type,
                  float value = 0.f, int flags = 0) {
  ParamInfo info{};
  info.type = static_cast<Core::Portable::ParamType>(type);
  std::strcpy(info.name, name);
  info.defaultValue = value;
  info.maxValue = 100.f;
  info.flags = flags;
  parent.addParameters(&info, 1, true);
}

void addGain(Component &parent) {
  addParameter(parent, "gain", ParamInfo::kFloat, 2.5f);
}

void addTitle(Component &parent) {
  addParameter(parent, "title", ParamInfo::kString);
  parent.findParameter("title")->fromString("hello", false);
}

void addPrivate(Component &parent) {
  addParameter(parent, "private", ParamInfo::kFloat, 42.f, ParamInfo::kPrivate);
}

ClientComponent &addClient(Component &parent, const char *name) {
  auto *child = new ClientComponent(name);
  parent.addChild(child);
  return *child;
}

void build(ClientComponent &root, std::string_view scenario) {
  if (scenario == "private")
    addPrivate(root);
  if (scenario == "values") {
    addGain(root);
    addTitle(root);
    addParameter(root, "color", ParamInfo::kColor);
    ColorParam::cast(root.findParameter("color"))->setColor(0xf1234567, false);
    addPrivate(root);
  }
  if (scenario == "mixed")
    addTitle(root);
  if (scenario == "children" || scenario == "mixed" || scenario == "pruned")
    addClient(root, "empty");
  if (scenario == "children" || scenario == "pruned") {
    auto *foreign = new Component("foreign");
    root.addChild(foreign);
    addGain(*foreign);
  }
  if (scenario == "children") {
    auto &branch = addClient(root, "branch");
    addGain(addClient(branch, "leaf"));
  }
  if (scenario == "mixed")
    addGain(addClient(root, "leaf"));
}

void printTree(const Attributes &attrs, const std::string &prefix) {
  for (int i = 0; i < attrs.countAttributes(); ++i) {
    const auto path = prefix + "/" + attrs.getAttributeName(i);
    const auto &attr = *attrs.getAttribute(i);
    switch (attr.getType()) {
    case AttributeValue::kAttributes:
      std::cout << "tree " << path << '\n';
      printTree(*attr.getAttributes(), path);
      break;
    case AttributeValue::kFloat:
      std::cout << "float " << path << ' ' << attr.getFloat() << '\n';
      break;
    case AttributeValue::kString:
      std::cout << "string " << path << ' ' << attr.getString() << '\n';
      break;
    case AttributeValue::kInt:
      std::cout << "int " << path << ' ' << attr.getInt() << '\n';
      break;
    default:
      std::abort();
    }
  }
}
} // namespace

int main(int argc, char *argv[]) {
  if (argc != 2)
    return 2;
  Presonus::UC::ClientRootComponent root("root");
  build(root, argv[1]);
  Attributes output(Core::Portable::AttributeAllocator::getDefault());
  std::cout << root.collectAll(output, root) << '\n';
  printTree(output, "");
}
