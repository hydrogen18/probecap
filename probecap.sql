
CREATE TABLE station(
	id serial not null UNIQUE,
	mac macaddr not null,
	firstSeen timestamp without time zone not null,
	lastSeen timestamp without time zone,
	PRIMARY KEY(mac)
);

grant usage,select on sequence station_id_seq to probecap;

CREATE TABLE ssid(
	id serial not null UNIQUE,
	name varchar(32) not null,
	PRIMARY KEY(name)
);

grant usage,select on sequence ssid_id_seq to probecap;

CREATE TABLE probe(
	station int not null,
	foreign key (station) references station(id),
	ssid int null,
	foreign key (ssid) references ssid(id) ,
	seen timestamp without time zone
);

CREATE TABLE beacon(
	station int not null,
	foreign key(station) references station(id),
	ssid int references ssid(id) null,
	seen timestamp without time zone
);
