create table guilds
(
    id         bigint                               not null
        constraint guilds_pk
            primary key,
    banned     boolean default false                not null,
    ban_reason text    default 'not provided'::text not null,
    joined     boolean default true                 not null
);

alter table guilds
    owner to pi;

create table guilds_log
(
    id    bigserial                           not null
        constraint guilds_log_pk
            primary key,
    time  timestamp default CURRENT_TIMESTAMP not null,
    type  text,
    value text
);

alter table guilds_log
    owner to pi;

create table prefixes
(
    guild_id bigint       not null,
    prefix   varchar(255) not null,
    constraint prefixes_pk
        primary key (guild_id, prefix)
);

alter table prefixes
    owner to pi;

create table updates
(
    id      serial                                 not null
        constraint updates_pk
            primary key,
    date    timestamp default CURRENT_TIMESTAMP    not null,
    content text      default 'not provided'::text not null
);

alter table updates
    owner to pi;

create unique index updates_date_uindex
    on updates (date);

create table users
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

alter table users
    owner to pi;

create unique index users_id_uindex
    on users (id);

create table users_avatar_log
(
    user_id   bigint                              not null,
    avatar    bytea                               not null,
    timestamp timestamp default CURRENT_TIMESTAMP not null,
    constraint users_avatar_log_pk
        primary key (user_id, timestamp)
);

alter table users_avatar_log
    owner to pi;

create table users_in_guilds
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

alter table users_in_guilds
    owner to pi;

create table users_log
(
    id    bigint    not null,
    time  timestamp not null,
    type  text,
    value text,
    constraint users_log_pk
        primary key (id, time)
);

alter table users_log
    owner to pi;

