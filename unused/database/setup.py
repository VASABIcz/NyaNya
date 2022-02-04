GLOBAL = """create table if not exists guilds
(
    id         bigint                               not null
        constraint guilds_pk
            primary key,
    banned     boolean default false                not null,
    ban_reason text    default 'not provided'::text not null,
    joined     boolean default true                 not null
);

create table if not exists guilds_log
(
    id    bigserial                           not null
        constraint guilds_log_pk
            primary key,
    time  timestamp default CURRENT_TIMESTAMP not null,
    type  text,
    value text
);

create table if not exists updates
(
    id      serial                                 not null
        constraint updates_pk
            primary key,
    date    timestamp default CURRENT_TIMESTAMP    not null,
    content text      default 'not provided'::text not null
);

create unique index if not exists updates_date_uindex
    on updates (date);

create table if not exists users
(
    id            bigint                               not null
        constraint users_pk
            primary key,
    name          text                                 not null,
    discriminator integer                              not null,
    banned        boolean default false                not null,
    ban_reason    text    default 'not provided'::text not null,
    constraint users_pk_2
        unique (name, discriminator)
);

create unique index if not exists users_id_uindex
    on users (id);

create table if not exists users_avatar_log
(
    user_id   bigint                              not null,
    avatar    bytea                               not null,
    timestamp timestamp default CURRENT_TIMESTAMP not null,
    constraint users_avatar_log_pk
        primary key (user_id, timestamp)
);

create table if not exists users_in_guilds
(
    guild_id bigint               not null
        constraint users_in_guilds_guilds_id_fk
            references guilds
            on update cascade on delete cascade,
    user_id  bigint               not null
        constraint users_in_guilds_users_id_fk
            references users
            on update cascade on delete cascade,
    points   integer default 0    not null,
    joined   boolean default true not null,
    constraint users_in_guilds_pk
        primary key (guild_id, user_id)
);

create table if not exists users_log
(
    id    bigint    not null,
    time  timestamp not null,
    type  text,
    value text,
    constraint users_log_pk
        primary key (id, time)
);

"""

INSTANCE = """
create table if not exists {id}_prefixes
(
    guild_id bigint       not null,
    prefix   varchar(255) not null,
    primary key (guild_id, prefix)
);
"""
