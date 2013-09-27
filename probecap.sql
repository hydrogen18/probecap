
CREATE TABLE station{
	id serial not null,
	mac char(6) not null,
	firstSeen timestamp without time zone not null,
	lastSeen timestamp without time zone,
	PRIMARY KEY(mac)
};

grant usage,select on sequence station_id_seq to probecap;

CREATE TABLE ssid{
	id serial not null
	name varchar(32) not null
};

grant usage,select on sequence ssid_id_seq to probecap;

CREATE TABLE probe{
	station int references station(id) not null,
	ssid int references ssid(id) null,
	seen timestamp without time zone
};

CREATE TABLE beacon{
	station int references station(id) not null,
	ssid int references ssid(id) null,
	seen timestamp without time zone
};
