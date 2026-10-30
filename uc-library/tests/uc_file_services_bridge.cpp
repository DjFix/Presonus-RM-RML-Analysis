#include "core/portable/corepersistence.h"
#include "presonus/uc/file_services.hpp"
#include <algorithm>
#include <cstring>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace presonus::uc {
struct FileServicesStateAccess {
  static void position(Presonus::UC::FileReader &v, std::uint32_t p) {
    v.position = p;
  }
  static std::uint32_t position(const Presonus::UC::FileReader &v) {
    return v.position;
  }
  static void success(Presonus::UC::FileWriter &v, bool p) { v.success = p; }
  static bool success(const Presonus::UC::FileWriter &v) { return v.success; }
  static void index(Presonus::UC::FileListReader &v, int p) { v.index = p; }
  static int index(const Presonus::UC::FileListReader &v) { return v.index; }
};
} // namespace presonus::uc
using namespace Core;
using namespace Core::Portable;
using namespace Presonus::UC;
using Access = presonus::uc::FileServicesStateAccess;
static std::string unhex(const std::string &s) {
  if (s == "-")
    return {};
  if (s.size() % 2)
    throw std::runtime_error("odd hex");
  std::string result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result.push_back(
        static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return result;
}
static std::string hex(const void *p, std::size_t n) {
  if (!n)
    return "-";
  constexpr char digits[] = "0123456789abcdef";
  std::string s;
  for (std::size_t i = 0; i < n; ++i) {
    auto b = static_cast<const unsigned char *>(p)[i];
    s += digits[b >> 4];
    s += digits[b & 15];
  }
  return s;
}
static std::string hex(const std::string &s) { return hex(s.data(), s.size()); }
static unsigned destroyed = 0;
static void *observedObject = nullptr;
static unsigned observedDeletes = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == observedObject)
    ++observedDeletes;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == observedObject)
    ++observedDeletes;
  __real__ZdlPvm(p, n);
}
// Test-only references to the compiler's real ABI variants, not invented app
// method declarations. Constructors and destructors are still defined normally.
extern "C" void baseC1(void *, IO::Stream *) asm(
    "_ZN8Presonus2UC18FileRequestHandlerC1EPN4Core2IO6StreamE");
extern "C" void baseC2(void *, IO::Stream *) asm(
    "_ZN8Presonus2UC18FileRequestHandlerC2EPN4Core2IO6StreamE");
extern "C" void
readerC1(void *, IO::Stream *,
         unsigned) asm("_ZN8Presonus2UC10FileReaderC1EPN4Core2IO6StreamEj");
extern "C" void
readerC2(void *, IO::Stream *,
         unsigned) asm("_ZN8Presonus2UC10FileReaderC2EPN4Core2IO6StreamEj");
extern "C" void
writerC1(void *,
         IO::Stream *) asm("_ZN8Presonus2UC10FileWriterC1EPN4Core2IO6StreamE");
extern "C" void
writerC2(void *,
         IO::Stream *) asm("_ZN8Presonus2UC10FileWriterC2EPN4Core2IO6StreamE");
extern "C" void baseD0(void *) asm("_ZN8Presonus2UC18FileRequestHandlerD0Ev");
extern "C" void baseD1(void *) asm("_ZN8Presonus2UC18FileRequestHandlerD1Ev");
extern "C" void baseD2(void *) asm("_ZN8Presonus2UC18FileRequestHandlerD2Ev");
extern "C" void readerD0(void *) asm("_ZN8Presonus2UC10FileReaderD0Ev");
extern "C" void readerD1(void *) asm("_ZN8Presonus2UC10FileReaderD1Ev");
extern "C" void writerD0(void *) asm("_ZN8Presonus2UC10FileWriterD0Ev");
extern "C" void writerD1(void *) asm("_ZN8Presonus2UC10FileWriterD1Ev");
class TestStream final : public IO::Stream {
public:
  std::string bytes;
  int forced = 0;
  bool forcing = false;
  int calls = 0, lastSize = 0;
  int64 pos = 0;
  ~TestStream() override { ++destroyed; }
  int64 getPosition() override { return pos; }
  int64 setPosition(int64 p, int mode) override {
    if (mode == 0)
      pos = p;
    else if (mode == 1)
      pos += p;
    else
      pos = static_cast<int64>(bytes.size()) + p;
    return pos;
  }
  int readBytes(void *p, int size) override {
    ++calls;
    lastSize = size;
    if (forcing) {
      if (forced > 0)
        for (int i = 0; i < std::min(size, forced); ++i)
          static_cast<unsigned char *>(p)[i] =
              static_cast<unsigned char>(i * 17 + 3);
      return forced;
    }
    auto n = std::max<int64>(
        0, std::min<int64>(size, static_cast<int64>(bytes.size()) - pos));
    if (n)
      std::memcpy(p, bytes.data() + pos, static_cast<std::size_t>(n));
    pos += n;
    return static_cast<int>(n);
  }
  int writeBytes(const void *p, int size) override {
    ++calls;
    lastSize = size;
    if (forcing)
      return forced;
    if (pos < 0 || size < 0 || pos + size > 1048576)
      return -1;
    if (pos + size > static_cast<int64>(bytes.size()))
      bytes.resize(static_cast<std::size_t>(pos + size));
    std::memcpy(bytes.data() + pos, p, static_cast<std::size_t>(size));
    pos += size;
    return size;
  }
};
static void eventFill(FileDataEvent &e) {
  e.idBits = 0x12345678;
  e.wordBits = {0x11223344, 0x55667788};
  e.data.fill(0xa5);
}
int main() {
  std::map<int, std::unique_ptr<Attributes>> owned;
  std::map<int, Attributes *> attrs;
  std::map<int, AttributeQueue *> queues;
  std::map<const void *, int> ids;
  int next = 1;
  auto registerAttr = [&](Attributes *p) {
    if (!p)
      return 0;
    if (ids.count(p))
      return ids[p];
    int id = next++;
    ids[p] = id;
    attrs[id] = p;
    return id;
  };
  auto registerQueue = [&](const AttributeQueue *p) {
    if (!p)
      return 0;
    if (ids.count(p))
      return ids[p];
    int id = next++;
    ids[p] = id;
    queues[id] = const_cast<AttributeQueue *>(p);
    return id;
  };
  for (std::string line; std::getline(std::cin, line);) {
    std::istringstream in(line);
    std::string op;
    in >> op;
    try {
      if (op == "quit") {
        std::cout << "OK\n" << std::flush;
        break;
      }
      if (op == "variant") {
        unsigned kind, hasStream;
        std::string ctor, dtor;
        in >> kind >> ctor >> dtor >> hasStream;
        const auto before = destroyed;
        auto *s = hasStream ? new TestStream : nullptr;
        void *storage = ::operator new(kind == 0   ? sizeof(FileRequestHandler)
                                       : kind == 1 ? sizeof(FileReader)
                                                   : sizeof(FileWriter));
        if (kind == 0)
          (ctor == "C1" ? baseC1 : baseC2)(storage, s);
        else if (kind == 1)
          (ctor == "C1" ? readerC1 : readerC2)(storage, s, 17);
        else
          (ctor == "C1" ? writerC1 : writerC2)(storage, s);
        auto *p = static_cast<FileRequestHandler *>(storage);
        IFileRequestHandler *iface = p;
        if (dynamic_cast<FileRequestHandler *>(iface) != p ||
            (kind == 1 && dynamic_cast<FileReader *>(iface) == nullptr) ||
            (kind == 2 && dynamic_cast<FileWriter *>(iface) == nullptr))
          throw std::runtime_error("app RTTI failed");
        bool equal = p->getStream() == s, read = false, write = false;
        FileDataEvent e;
        if (kind == 0) {
          read = p->readData(e);
          write = p->writeData(e);
        }
        observedObject = storage;
        observedDeletes = 0;
        if (dtor == "finish")
          p->finish();
        else if (kind == 0)
          (dtor == "D0" ? baseD0 : dtor == "D1" ? baseD1 : baseD2)(storage);
        else if (kind == 1)
          (dtor == "D0" ? readerD0 : readerD1)(storage);
        else
          (dtor == "D0" ? writerD0 : writerD1)(storage);
        const auto deletes = observedDeletes;
        observedObject = nullptr;
        // No post-lifetime vptr/object reads. D1/D2 leave only raw storage.
        if (dtor != "D0" && dtor != "finish")
          ::operator delete(storage);
        std::cout << equal << ' ' << read << ' ' << write << ' '
                  << destroyed - before << ' ' << deletes;
      } else if (op == "read") {
        std::uint32_t total, pos;
        int result;
        unsigned part, count;
        in >> total >> pos >> result >> part >> count;
        auto *s = new TestStream;
        s->forcing = true;
        s->forced = result;
        FileReader reader(s, total);
        Access::position(reader, pos);
        FileDataEvent e;
        eventFill(e);
        e.partBits = part;
        e.count = count;
        bool r = reader.readData(e);
        std::cout << r << ' ' << Access::position(reader) << ' '
                  << e.wordBits[0] << ' ' << e.wordBits[1] << ' ' << e.partBits
                  << ' ' << e.count << ' ' << e.idBits << ' ' << s->calls << ' '
                  << s->lastSize << ' ' << hex(e.data.data(), e.data.size());
      } else if (op == "write") {
        unsigned part, count, old;
        int result;
        in >> part >> count >> result >> old;
        auto *s = new TestStream;
        s->forcing = true;
        s->forced = result;
        FileWriter writer(s);
        Access::success(writer, old != 0);
        FileDataEvent e;
        eventFill(e);
        e.partBits = part;
        e.count = count;
        bool r = writer.writeData(e);
        std::cout << r << ' ' << Access::success(writer) << ' ' << s->calls
                  << ' ' << s->lastSize;
      } else if (op == "a_new") {
        auto p = std::make_unique<Attributes>(AttributeAllocator::getDefault());
        int id = registerAttr(p.get());
        owned[id] = std::move(p);
        std::cout << id;
      } else if (op == "a_queue") {
        int id;
        std::string key;
        in >> id >> key;
        std::cout << registerQueue(attrs.at(id)->getQueue(unhex(key).c_str()));
      } else if (op == "a_makequeue") {
        int id;
        std::string key;
        in >> id >> key;
        std::cout << registerQueue(attrs.at(id)->makeQueue(unhex(key).c_str()));
      } else if (op == "q_append") {
        int q, id;
        in >> q >> id;
        std::cout << registerAttr(
            queues.at(q)->appendAttributes(attrs.at(id)->getAllocator()));
      } else if (op == "q_snapshot") {
        int q;
        in >> q;
        const auto &values = queues.at(q)->getValues();
        std::cout << values.count();
        for (int i = 0; i < values.count(); ++i) {
          auto *v = values.at(i);
          std::cout << ' ' << (v ? v->getType() : 0) << ' '
                    << (v ? registerAttr(v->getAttributes()) : 0);
        }
      } else if (op == "a_setstr") {
        int id;
        std::string key, value;
        in >> id >> key >> value;
        attrs.at(id)->set(unhex(key).c_str(), unhex(value).c_str(), false);
        std::cout << "OK";
      } else if (op == "a_setint") {
        int id;
        std::string key;
        int64 value;
        in >> id >> key >> value;
        attrs.at(id)->set(unhex(key).c_str(), value);
        std::cout << "OK";
      } else if (op == "a_getstr") {
        int id;
        std::string key;
        in >> id >> key;
        const char *value = attrs.at(id)->getString(unhex(key).c_str());
        std::cout << hex(value ? std::string(value) : std::string());
      } else if (op == "a_getint") {
        int id;
        std::string key;
        in >> id >> key;
        std::cout << attrs.at(id)->getInt(unhex(key).c_str());
      } else if (op == "a_load") {
        int id;
        std::string data;
        in >> id >> data;
        TestStream s;
        s.bytes = unhex(data);
        Archiver archive(&s, Archiver::kJSON, 0);
        std::cout << archive.load(*attrs.at(id));
      } else if (op == "a_save") {
        int id;
        in >> id;
        TestStream s;
        Archiver archive(&s, Archiver::kJSON, 1);
        bool r = archive.save(*attrs.at(id));
        std::cout << r << ' ' << hex(s.bytes);
      } else if (op == "a_destroy") {
        int id;
        in >> id;
        owned.erase(id);
        std::cout << "OK";
      } else if (op == "cstring") {
        std::string value;
        in >> value;
        CStringBuffer<128> text(unhex(value).c_str());
        std::cout << hex(std::string(text.str()));
      } else if (op == "list_read") {
        std::string data;
        int index;
        in >> data >> index;
        FileListReader reader;
        Access::index(reader, index);
        TestStream s;
        s.bytes = unhex(data);
        bool loaded = reader.fromStream(s);
        FileListReader::Entry entry;
        entry.name = "sentinel-name";
        entry.title = "sentinel-title";
        entry.size = -123;
        entry.directory = true;
        bool result = reader.getNextEntry(entry);
        std::cout << loaded << ' ' << result << ' ' << Access::index(reader)
                  << ' ' << hex(std::string(entry.name.str())) << ' '
                  << hex(std::string(entry.title.str())) << ' ' << entry.size
                  << ' ' << entry.directory;
      } else if (op == "list_write") {
        unsigned n;
        in >> n;
        FileListWriter writer;
        for (unsigned i = 0; i < n; ++i) {
          std::string name, title;
          long long size;
          unsigned dir;
          in >> name >> title >> size >> dir;
          auto a = unhex(name),
               b = title == "NULL" ? std::string() : unhex(title);
          writer.addEntry(a.c_str(), title == "NULL" ? nullptr : b.c_str(),
                          size, dir != 0);
        }
        TestStream s;
        writer.toStream(s);
        std::cout << s.pos << ' ' << hex(s.bytes);
      } else if (op == "lifecycle") {
        unsigned kind, hasStream, finish;
        in >> kind >> hasStream >> finish;
        auto before = destroyed;
        auto *s = hasStream ? new TestStream : nullptr;
        FileRequestHandler *p =
            kind == 0 ? new FileRequestHandler(s)
            : kind == 1
                ? static_cast<FileRequestHandler *>(new FileReader(s, 17))
                : static_cast<FileRequestHandler *>(new FileWriter(s));
        bool equal = p->getStream() == s;
        FileDataEvent e;
        eventFill(e);
        bool read = false, write = false;
        if (kind == 0) {
          read = p->readData(e);
          write = p->writeData(e);
        }
        if (finish)
          p->finish();
        else
          delete p;
        std::cout << equal << ' ' << read << ' ' << write << ' '
                  << (destroyed - before);
      } else
        throw std::runtime_error("unknown command");
      std::cout << '\n' << std::flush;
    } catch (const std::exception &e) {
      std::cout << "ERROR " << e.what() << '\n' << std::flush;
      return 1;
    }
  }
}
