#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include "parser.h"

namespace py = pybind11;

template<size_t N>
auto set_char_array(char (Packet::*pm)[N]) {
    return [pm](Packet &p, const std::string &value) {
        if (value.length() <= N) {
            std::memcpy(p.*pm, value.c_str(), value.length());
            if (value.length() < N) {
                std::memset((p.*pm) + value.length(), 0, N - value.length());
            }
        } else {
            throw std::runtime_error("String is too long for char array assignment!");
        }
    };
}

PYBIND11_MODULE(twse_udp_resolver, m) {
    m.doc() = "TWSE UDP Resolver (Python interface)"; // optional module docstring

    py::class_<Packet>(m, "Packet")
        .def(py::init<>())
        .def_readwrite("esc_code", &Packet::esc_code)
        .def_readwrite("message_length", &Packet::message_length)
        .def_readwrite("business_type", &Packet::business_type)
        .def_readwrite("format_code", &Packet::format_code)
        .def_readwrite("format_version", &Packet::format_version)
        .def_readwrite("transmission_number", &Packet::transmission_number)
        .def_property("stock_code",
            [](const Packet &p) { return std::string(p.stock_code, 6); },
            [](Packet &p, const std::string &s) {
                std::strncpy(p.stock_code, s.c_str(), 6);
            })
        .def_readwrite("match_time", &Packet::match_time)
        .def_readwrite("display_item", &Packet::display_item)
        .def_readwrite("limit_up_limit_down", &Packet::limit_up_limit_down)
        .def_readwrite("status_note", &Packet::status_note)
        .def_readwrite("cumulative_volume", &Packet::cumulative_volume)
        .def_readwrite("prices", &Packet::prices)
        .def_readwrite("quantities", &Packet::quantities)
        .def_property("warrant_A", [](const Packet &p) { return py::bytes(p.warrant_A, 16); }, set_char_array<16>(&Packet::warrant_A))
        .def_property("separator", [](const Packet &p) { return py::bytes(p.separator, 2); }, set_char_array<2>(&Packet::separator))
        .def_property("warrant_B", [](const Packet &p) { return py::bytes(p.warrant_B, 16); }, set_char_array<16>(&Packet::warrant_B))
        .def_property("warrant_C", [](const Packet &p) { return py::bytes(p.warrant_C, 8); }, set_char_array<8>(&Packet::warrant_C))
        .def_property("warrant_D", [](const Packet &p) { return py::bytes(p.warrant_D, 2); }, set_char_array<2>(&Packet::warrant_D))
        .def_property("warrant_E", [](const Packet &p) { return py::bytes(p.warrant_E, 2); }, set_char_array<2>(&Packet::warrant_E))
        .def_property("warrant_F", [](const Packet &p) { return py::bytes(p.warrant_F, 2); }, set_char_array<2>(&Packet::warrant_F))
        .def_property("warrant_G", [](const Packet &p) { return py::bytes(p.warrant_G, 2); }, set_char_array<2>(&Packet::warrant_G))
        .def_readwrite("checksum", &Packet::checksum)
        .def_readwrite("terminal_code", &Packet::terminal_code);

    py::class_<Parser>(m, "Parser")
        .def(py::init<>())
        .def("start_loop", &Parser::start_loop, "Start the UDP stream parsing loop")
        .def("end_loop", &Parser::end_loop, "Stop the parsing loop")
        .def("set_multicast", &Parser::set_multicast, "Sets the parameter of multicast")
        .def("set_allowed_format_codes", &Parser::set_allowed_format_codes, "Set the allowed format codes");
}