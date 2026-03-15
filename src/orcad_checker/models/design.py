from __future__ import annotations

from pydantic import BaseModel, Field


class Pin(BaseModel):
    number: str
    name: str
    type: str = ""
    net: str = ""


class Component(BaseModel):
    refdes: str
    part_name: str = ""
    value: str = ""
    footprint: str = ""
    part_number: str = ""
    library: str = ""
    page: str = ""
    properties: dict[str, str] = Field(default_factory=dict)
    pins: list[Pin] = Field(default_factory=list)


class NetConnection(BaseModel):
    refdes: str
    pin_number: str
    pin_name: str = ""


class Net(BaseModel):
    name: str
    is_power: bool = False
    connections: list[NetConnection] = Field(default_factory=list)


class UnconnectedPin(BaseModel):
    refdes: str
    pin_number: str
    pin_name: str = ""


class Page(BaseModel):
    name: str
    title: str = ""
    page_number: int = 0


class HierarchicalBlock(BaseModel):
    instance: str
    source_schematic: str = ""
    page: str = ""


class Hierarchy(BaseModel):
    top_level: str = ""
    pages: list[Page] = Field(default_factory=list)
    hierarchical_blocks: list[HierarchicalBlock] = Field(default_factory=list)


class Design(BaseModel):
    schema_version: str = "1.0.0"
    design_name: str = ""
    export_timestamp: str = ""
    source_file: str = ""
    components: list[Component] = Field(default_factory=list)
    nets: list[Net] = Field(default_factory=list)
    unconnected_pins: list[UnconnectedPin] = Field(default_factory=list)
    power_nets: list[str] = Field(default_factory=list)
    hierarchy: Hierarchy = Field(default_factory=Hierarchy)
