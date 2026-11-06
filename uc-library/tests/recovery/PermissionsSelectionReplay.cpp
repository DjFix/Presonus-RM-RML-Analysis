#include "core/portable/corepersistence.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>
using namespace Core::Portable;
using Presonus::UC::ClientSubscription;
namespace {
void *watched = nullptr;
bool released = false;
bool trackAllocation = false, allocationOrdered = false;
struct Tree : Component {
  void attach(Parameter *p) { paramList.add(p); }
  void detach(Parameter *p) { paramList.remove(p); }
};
struct Observer : Component {
  std::vector<int> events;
  void paramChanged(Parameter *, int message) override {
    if (message == Parameter::kChanged || message == Parameter::kRangeChanged)
      events.push_back(message == Parameter::kChanged ? 0 : 1);
  }
};
std::vector<std::string> split(const std::string &s, char delim) {
  std::vector<std::string> result;
  std::stringstream stream(s);
  std::string part;
  while (std::getline(stream, part, delim))
    result.push_back(part);
  if (!s.empty() && s.back() == delim)
    result.emplace_back();
  return result;
}
void snapshot(const ClientSubscription &s) {
  std::cout << "{\"id\":" << s.sourcePortIdentifier() << ",\"initial\":"
            << (s.sourcePortInitialState() ? "true" : "false")
            << ",\"strings\":[";
  const char *values[] = {s.sourcePortName().str(), s.sourcePortApp().str(),
                          s.sourcePortDevice().str(),
                          s.sourcePortIdentity().str(),
                          s.sourcePortDisplay().str()};
  for (int i = 0; i < 5; ++i) {
    if (i)
      std::cout << ',';
    std::cout << std::quoted(values[i]);
  }
  std::cout << "]}";
}
} // namespace
void *operator new(std::size_t n) {
  if (trackAllocation)
    allocationOrdered = watched == nullptr || released;
  if (auto *p = std::malloc(n ? n : 1))
    return p;
  throw std::bad_alloc();
}
void operator delete(void *p) noexcept {
  if (p && p == watched)
    released = true;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
int main(int argc, char **argv) {
  try {
    if (argc != 9)
      return 2;
    std::string op = argv[1];
    int id = std::stoi(argv[2]);
    if (op == "ctor") {
      alignas(ClientSubscription)
          std::array<unsigned char, sizeof(ClientSubscription)>
              bytes;
      bytes.fill(0xa5);
      auto *client = new (bytes.data()) ClientSubscription(id);
      for (auto *buffer :
           {&client->sourcePortName(), &client->sourcePortApp(),
            &client->sourcePortDevice(), &client->sourcePortIdentity(),
            &client->sourcePortDisplay(), &client->sourcePortSixth()})
        for (int i = 1; i < 64; ++i)
          if (static_cast<unsigned char>(buffer->str()[i]) != 0xa5)
            return 7;
      snapshot(*client);
      client->~ClientSubscription();
      return 0;
    }
    std::vector<std::unique_ptr<ClientSubscription>> owned;
    Core::Vector<const ClientSubscription *> collection;
    for (const auto &spec : split(argv[4], ';')) {
      if (spec == "null") {
        collection.add(nullptr);
        continue;
      }
      auto fields = split(spec, '|');
      if (fields.size() != 6)
        return 3;
      auto client = std::make_unique<ClientSubscription>(std::stoi(fields[0]));
      client->sourcePortSetName(Core::CStringBuffer<64>(fields[1].c_str()));
      client->sourcePortSetApp(Core::CStringBuffer<64>(fields[2].c_str()));
      client->sourcePortSetDevice(Core::CStringBuffer<64>(fields[3].c_str()));
      client->sourcePortSetIdentity(Core::CStringBuffer<64>(fields[4].c_str()));
      client->sourcePortSetDisplay(Core::CStringBuffer<64>(fields[5].c_str()));
      collection.add(client.get());
      owned.push_back(std::move(client));
    }
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.bindClients(collection);
    if (op == "get") {
      const auto *p = mixer.getClient(id);
      int index = -1;
      for (int i = 0; i < collection.count(); ++i)
        if (p && p == collection.at(i))
          index = i;
      std::cout << index;
      return 0;
    }
    if (op == "invariant") {
      mixer.clientCount++;
      bool caught = false;
      try {
        (void)mixer.numClients();
      } catch (const std::logic_error &) {
        caught = true;
      }
      std::cout << (caught ? "true" : "false");
      return caught ? 0 : 1;
    }
    ParamInfo di = {
        ParamInfo::kList, 0,       "devices", 0,       -1,     0, 0, 1, 0,
        nullptr,          nullptr, nullptr,   nullptr, nullptr};
    ParamInfo si = PARAM_STRING(4, "access", ParamInfo::kStorable);
    ParamInfo ni = {
        ParamInfo::kInt, 4,       "numeric", 0,       10,     0, 0, 1, 0,
        nullptr,         nullptr, nullptr,   nullptr, nullptr};
    ListParam devices(di);
    StringParam access(si);
    NumericParam numeric(ni);
    Tree tree;
    const std::string type = argv[6];
    Parameter *parameter = type == "string" ? static_cast<Parameter *>(&access)
                           : type == "numeric"
                               ? static_cast<Parameter *>(&numeric)
                               : nullptr;
    if (parameter)
      tree.attach(parameter);
    struct Detach {
      Tree &tree;
      Parameter *p;
      ~Detach() {
        if (p)
          tree.detach(p);
      }
    } detach{tree, parameter};
    access.setDefaultText("old");
    access.fromString("initial", false);
    for (int i = 0; i < std::stoi(argv[5]); ++i)
      devices.appendString("seed");
    if (devices.getStringCount() > 1)
      devices.setValue(devices.getStringCount() - 1, false);
    Observer observer;
    devices.addObserver(&observer);
    struct Unobserve {
      ListParam &p;
      Observer &o;
      ~Unobserve() { p.removeObserver(&o); }
    } unobserve{devices, observer};
    Presonus::Mixer::PermissionsBindings bindings;
    bindings.mixer = &mixer;
    bindings.deviceList = &devices;
    bindings.accessCodeParameters = &tree;
    ClientSubscription previous(-7);
    previous.sourcePortSetIdentity(Core::CStringBuffer<64>(argv[3]));
    Presonus::Mixer::PermissionsComponent permissions(bindings);
    if (std::string(argv[3]) != "null")
      permissions.portableOwnSelected(&previous);
    if (op == "copy" || op == "set") {
      const auto *source = mixer.getClient(id);
      watched = const_cast<ClientSubscription *>(bindings.selectedSnapshot);
      released = false;
      allocationOrdered = false;
      trackAllocation = true;
      if (op == "copy")
        permissions.copyToSelected(*source);
      else
        permissions.setSelectedClient(source);
      trackAllocation = false;
      if (!allocationOrdered)
        return 8;
      std::cout << "{\"snapshot\":";
      snapshot(*bindings.selectedSnapshot);
      std::cout << ",\"released\":" << (watched && released ? "true" : "false")
                << "}";
      watched = nullptr;
      return 0;
    }
    std::filesystem::create_directories(argv[8]);
    mixer.applicationDataRoot = argv[8];
    mixer.deviceDataFolder = "selection";
    if (op == "init") {
      if (std::string(argv[7]) != "absent") {
        Core::Portable::FileName filename;
        permissions.getAccessCodeFileName(filename);
        Attributes attrs(AttributeAllocator::getDefault());
        attrs.set("access", argv[7]);
        ArchiveUtils::saveToFile(filename.str(), attrs);
      }
      permissions.init();
    } else
      permissions.updateDevices();
    std::cout << "{\"list\":[";
    for (int i = 0; i < devices.getStringCount(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << std::quoted(devices.getStringAt(i));
    }
    std::cout << "],\"value\":" << devices.getValue() << ",\"events\":[";
    for (unsigned i = 0; i < observer.events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << observer.events[i];
    }
    std::cout << "],\"access\":" << std::quoted(access.getText().str())
              << ",\"devices\":[";
    if (permissions.portableDeviceCount() == 0)
      std::cout << "null";
    for (int i = 0; i < permissions.portableDeviceCount(); ++i) {
      if (i)
        std::cout << ',';
      std::cout
          << permissions.portableDeviceStorage()[i]->sourcePortIdentifier();
    }
    std::cout << "]}";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what();
    return 1;
  }
}
