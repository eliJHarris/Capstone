create table students(
   studentID int AUTO_INCREMENT,
   username varchar(15),
   email varchar(120),
   primary key(studentID)
)engine=innodb;

insert into students(username,email) values('jsmith','jim.smith@gmail.com');
insert into students(username,email) values('mjones','mjones@gmail.com');
insert into students(username,email) values('rwilson','rick.wilson@gmail.com');
insert into students(username,email) values('kjohnson','kjohnson@gmail.com');
insert into students(username,email) values('bwilliams','bwilliams@gmail.com');
